"""R192: audit saved artifacts only; no production imports or scheduling search."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'experiments/r192-mobile-backbone-static-audit'
PREPARED = ROOT / 'experiments/r186-general-region-full336-prepared'
LARGE = Path(r'G:\Hackathon-stage2-artifacts\project18\r187-general-region-full336')
REF = re.compile(r't#([1-9][0-9]*)\Z')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def gz_records(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        yield from (json.loads(line) for line in stream)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def distance(ref):
    match = REF.fullmatch(ref)
    assert match, ('bad_reference', ref)
    return int(match[1])


def original(data):
    rows = data['instructions']
    args, deps, users = [], [], defaultdict(list)
    assert len({row['id'] for row in rows}) == len(rows)
    for node, row in enumerate(rows):
        # IDs are external labels; t# distances and saved original_order identify
        # array positions. sparse_live deliberately contains nonconsecutive IDs.
        assert isinstance(row['id'], int)
        op = row['op']
        assert op in {'GET', 'SET', 'ADD', 'MULW'}
        expected = 0 if op == 'GET' else 1 if op == 'SET' else 2
        incoming = tuple(node - distance(ref) for ref in row.get('inputs', []))
        assert len(incoming) == expected
        assert all(0 <= src < node and rows[src]['op'] != 'SET' for src in incoming)
        args.append(incoming)
        dependency = set(incoming)
        if op in {'GET', 'SET'}:
            assert isinstance(row['reg'], str)
            for prior in range(node):
                old = rows[prior]
                if old['op'] in {'GET', 'SET'} and old['reg'] == row['reg'] and (op == 'SET' or old['op'] == 'SET'):
                    dependency.add(prior)  # Independent pairwise RAW/WAR/WAW.
        deps.append(dependency)
        for src in sorted(set(incoming)):
            users[src].append(node)
    return rows, args, deps, users


def replay(data, candidate):
    rows, args, deps, users = original(data)
    order = candidate['original_order']
    assert len(order) == len(rows) and set(order) == set(range(len(rows)))
    output = candidate['output']
    assert output['block_id'] == data['block_id']
    physical = output['optimized_instructions']
    history, emitted, births, original_slots = [], set(), {}, {}
    origins, per_identity = Counter(), Counter()
    cursor, width = 0, 1 << data['bit_width']
    for slot, row in enumerate(physical):
        assert row['id'] == slot
        op = row['op']
        if op == 'COPY':
            d = distance(row['source'])
            assert 1 <= d <= min(width, slot)
            identity = history[slot - d]
            assert identity is not None
            assert not row.get('inputs') and 'reg' not in row
            origins[rows[identity]['op']] += 1
            per_identity[identity] += 1
        else:
            assert cursor < len(order)
            identity = order[cursor]
            source = rows[identity]
            assert op == source['op'] and deps[identity] <= emitted
            assert row.get('reg') == source.get('reg')
            refs = row.get('inputs', [])
            assert len(refs) == len(args[identity])
            actual = []
            for ref in refs:
                d = distance(ref)
                assert 1 <= d <= min(width, slot)
                actual.append(history[slot - d])
            assert tuple(actual) == args[identity], ('ordered_identity', identity, actual, args[identity])
            births[identity] = cursor
            original_slots[identity] = slot
            cursor += 1
            emitted.add(identity)
            if op == 'SET':
                identity = None  # SET advances the physical window without a temporary.
        history.append(identity)
    assert cursor == len(rows)
    assert len(physical) == len(rows) + sum(per_identity.values())
    assert candidate['copies'] == sum(per_identity.values())
    details = []
    for identity, count in per_identity.most_common(8):
        ranks = [births[user] for user in users[identity]]
        details.append({'id': identity, 'op': rows[identity]['op'], 'copies': count,
            'birth_original_rank': births[identity], 'direct_consumer_count': len(ranks),
            'first_consumer_rank': min(ranks) if ranks else None,
            'last_consumer_rank': max(ranks) if ranks else None,
            'birth_to_first_use_original_gap': min(ranks) - births[identity] if ranks else None})
    return {'copy_origins': dict(origins), 'copied_identities': details,
            'original_physical_slots': original_slots, 'physical_identities': history,
            'physical_rows': len(physical), 'copies': sum(per_identity.values())}


def semantic_check(data, candidate, mode, seed=0):
    """Independently interpret original and physical programs, preserving register effects."""
    rows, args, _, _ = original(data)
    regs = {row['reg'] for row in rows if row['op'] in {'GET', 'SET'}}
    symbolic = mode == 'symbolic'
    bits, signed = (0, False) if symbolic else mode

    def wrap(value):
        value %= 1 << bits
        return value - (1 << bits) if signed and value >= 1 << (bits - 1) else value

    initial = {reg: ('initial', reg) if symbolic else wrap(int.from_bytes(hashlib.sha256(f'{seed}:{reg}'.encode()).digest()[:8], 'big')) for reg in regs}

    def operation(op, incoming):
        if symbolic:
            return (op, *incoming)  # Ordered opaque operations, no algebraic rewriting/aliasing.
        return wrap(incoming[0] + incoming[1] if op == 'ADD' else incoming[0] * incoming[1])

    memory, values, writes = dict(initial), [], []
    for index, row in enumerate(rows):
        op = row['op']
        incoming = [values[src] for src in args[index]]
        if op == 'GET':
            value = memory[row['reg']]
        elif op == 'SET':
            memory[row['reg']] = incoming[0]
            writes.append((index, row['reg'], incoming[0]))
            value = None
        else:
            value = operation(op, incoming)
        values.append(value)
    physical_memory, history, produced, physical_writes = dict(initial), [], {}, []
    cursor = 0
    for row in candidate['output']['optimized_instructions']:
        op = row['op']
        if op == 'COPY':
            value = history[-distance(row['source'])]
        else:
            identity = candidate['original_order'][cursor]
            cursor += 1
            incoming = [history[-distance(ref)] for ref in row.get('inputs', [])]
            if op == 'GET':
                value = physical_memory[row['reg']]
            elif op == 'SET':
                value = None
                physical_memory[row['reg']] = incoming[0]
                physical_writes.append((identity, row['reg'], incoming[0]))
            else:
                value = operation(op, incoming)
            produced[identity] = value
        history.append(value)
    assert produced == dict(enumerate(values))
    assert physical_memory == memory
    assert sorted(physical_writes) == sorted(writes)
    return {'mode': str(mode), 'seed': seed, 'all_original_values': True, 'all_registers': True, 'all_original_writes': True}


def interval_proof(data, baseline):
    """Arithmetic certificates over fixed intervals, not a schedule oracle."""
    check = replay(data, baseline)
    assert len(data['instructions']) == 45 and data['bit_width'] == 2
    assert baseline['original_order'] == list(range(45))
    rows, args, _, _ = original(data)
    assert rows[0] == {'id': 0, 'op': 'GET', 'reg': 'a'}
    assert rows[43]['op'] == 'MULW' and args[43] == (0, 0)
    certificates = []
    prefix_blocked, age_blocked = 0, 0
    physical = baseline['output']['optimized_instructions']
    for left in range(45):
        for right in range(left, min(45, left + 32)):
            cut = check['original_physical_slots'][left]
            fixed_copies = sum(row['op'] == 'COPY' for row in physical[:cut])
            item = {'L': left, 'R': right, 'length': right - left + 1, 'fixed_prefix_physical_rows': cut,
                    'fixed_prefix_COPY': fixed_copies}
            if fixed_copies:
                item['obstruction'] = 'preserved_prefix_contains_COPY'
                prefix_blocked += 1
            else:
                assert left <= 3 and right <= 34 and 43 > right
                latest_get_slot = right if left == 0 else 0
                # Under hypothetical zero COPY, every physical slot is one original;
                # fixed suffix starts after exactly R+1 originals, so MUL43 stays at43.
                age = 43 - latest_get_slot
                assert age > 4
                item.update({'obstruction': 'original_identity_GET0_not_addressable_at_fixed_suffix_MUL43',
                             'latest_possible_GET0_slot': latest_get_slot, 'MUL43_slot_if_zero_COPY': 43,
                             'minimum_GET0_age': age, 'W': 4})
                age_blocked += 1
            certificates.append(item)
    assert len(certificates) == 944 and prefix_blocked + age_blocked == 944
    return {'scope': 'strict original-once identity, reorder one contiguous <=32 original-rank interval; all physical prefix rows including COPY before first regional original fixed; suffix original order fixed, suffix COPY may be removed (more permissive than physical suffix fixed). No new GET/recompute/alias.',
            'count': len(certificates), 'prefix_obstructions': prefix_blocked, 'age_obstructions': age_blocked,
            'minimum_age_among_age_certificates': min(row['minimum_GET0_age'] for row in certificates if 'minimum_GET0_age' in row),
            'certificates': certificates}


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    DEST.mkdir(exist_ok=False)
    start = perf_counter()
    try:
        old = load(ROOT / 'experiments/r190-mobile-backbone-static/source-provenance.json')
        validated_files = []
        for entry in old['files']:
            live = ROOT / entry['path']
            frozen = ROOT / 'experiments/r190-mobile-backbone-static/source' / entry['path']
            assert digest(live) == entry['sha256'] and digest(frozen) == entry['sha256']
            validated_files.append(entry)
        hand = load(ROOT / 'research/level-stage/mobile-backbone-hand45.json')
        hand_outputs = []
        for label in ('baseline', 'manual_mobile_witness'):
            result = replay(hand['input'], hand[label])
            semantic = [semantic_check(hand['input'], hand[label], 'symbolic')]
            for mode in ((8, True), (16, False), (32, True)):
                for seed in (19001, 19002, 19003):
                    semantic.append(semantic_check(hand['input'], hand[label], mode, seed))
            hand_outputs.append({'label': label, 'physical_rows': result['physical_rows'], 'copies': result['copies'],
                                 'copy_origins': result['copy_origins'], 'semantic_checks': semantic})
        assert [row['copies'] for row in hand_outputs] == [13, 0]
        proof = interval_proof(hand['input'], hand['baseline'])
        write(DEST / 'interval-certificates.json', proof)
        original_report = load(ROOT / 'experiments/r189-general-region-remaining-static/report.json')
        records = {row['sha256']: row for row in original_report['records']}
        actual = load(ROOT / 'experiments/r187-general-region-full336/report.json')
        actual_records = {row['sha256']: row for row in actual['records']}
        lower = load(ROOT / 'experiments/r143-root-lifetime-summary/report.json')
        lower_records = {row['sha256']: row for row in lower['records']}
        statuses, family_origins, family_copies, audited = Counter(), defaultdict(Counter), Counter(), []
        checked = 0
        for case in gz_records(PREPARED / 'inputs.jsonl.gz'):
            data, family = case['input'], case['family']
            key = fingerprint(data)
            declared, saved = records[key], actual_records[key]
            assert declared['family'] == family and declared['copies'] == saved['after_copies']
            assert declared['necessary_lower'] == lower_records[key]['joint_lower']
            statuses[saved['source_status']] += 1
            if saved['after_copies'] is None:
                assert saved['source_status'] != 'verified'
                continue
            path = LARGE / f'{key[:16]}-best.json.gz'
            if not path.exists():
                path = PREPARED / 'initials' / f'{key}.json.gz'
            candidate = next(gz_records(path))
            result = replay(data, candidate)
            assert result['copies'] == declared['copies']
            assert result['copy_origins'] == declared['copy_origins']
            assert result['copied_identities'] == declared['copied_identities']
            family_origins[family].update(result['copy_origins'])
            family_copies[family] += result['copies']
            checked += 1
            audited.append({'sha256': key, 'family': family, 'copies': result['copies'], 'source_output': str(path),
                            'compressed_sha256': digest(path), 'copy_origins': result['copy_origins'],
                            'copied_identities': result['copied_identities']})
        assert checked == 272 and len(records) == 336 and sum(statuses.values()) == 336
        for family, row in original_report['families'].items():
            assert dict(family_origins[family]) == row['copy_origins']
            assert family_copies[family] == row['copies']
        assert sum(family_copies.values()) == 192859
        write(DEST / 'audited-records.json', audited)
        report = {'phase': 'Static saved-output audit only; no scheduling, oracle, baseline rerun or production imports.',
                  'hand_outputs': hand_outputs, 'continuous_interval_proof': {k: v for k, v in proof.items() if k != 'certificates'},
                  'saved_whole_identity_hazard_replays': checked, 'all_input_count': 336, 'statuses': dict(statuses),
                  'COPY_total': sum(family_copies.values()), 'family_COPY': dict(family_copies),
                  'family_COPY_origins': {key: dict(value) for key, value in family_origins.items()},
                  'all_top8_copy_identity_birth_and_use_fields_match_R189': True,
                  'necessary_bound_scope': original_report['necessary_scope'], 'quality_gap_scope': original_report['gap_scope'],
                  'historical_hashes_checked': validated_files,
                  'source_report_sha256': digest(ROOT / 'experiments/r187-general-region-full336/report.json'),
                  'source_bound_sha256': digest(ROOT / 'experiments/r143-root-lifetime-summary/report.json'),
                  'elapsed_seconds': perf_counter() - start}
        write(DEST / 'report.json', report)
        files = [Path(__file__), ROOT / 'research/level-stage/mobile-backbone-next-plan.md',
                 ROOT / 'research/level-stage/mobile-backbone-hand45.json',
                 ROOT / 'scripts/analyze_general_region_remaining_static.py',
                 ROOT / 'experiments/r189-general-region-remaining-static/report.json',
                 ROOT / 'experiments/r189-general-region-remaining-static/source-provenance.json']
        frozen = []
        for path in files:
            relative = path.relative_to(ROOT)
            target = DEST / 'source' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            frozen.append({'path': relative.as_posix(), 'sha256': digest(path), 'bytes': path.stat().st_size})
        for name in ('report.json', 'interval-certificates.json', 'audited-records.json'):
            path = DEST / name
            frozen.append({'path': name, 'sha256': digest(path), 'bytes': path.stat().st_size})
        write(DEST / 'manifest.json', {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'files': frozen,
              'aggregate_sha256': fingerprint(frozen), 'phase': report['phase']})
        print(json.dumps({'report': str(DEST / 'report.json'), 'report_sha256': digest(DEST / 'report.json'),
                          'manifest_sha256': digest(DEST / 'manifest.json'), 'whole_replays': checked,
                          'COPY_total': report['COPY_total'], 'hand_COPY': [row['copies'] for row in hand_outputs],
                          'intervals': proof['count'], 'elapsed_seconds': report['elapsed_seconds']}))
    except BaseException as error:
        write(DEST / 'failure.json', {'type': type(error).__name__, 'message': str(error),
                                     'utc': datetime.now(timezone.utc).isoformat()})
        raise


if __name__ == '__main__':
    main()
