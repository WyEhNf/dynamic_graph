"""Source-only R193 freeze / proposed R194 one-shot small functionality.

--prepare is metadata/fixture construction, AST parsing and file copying only.
--run calls the new solver/reference and MUST await the parent's review gate.
No baseline/default/full336/old-oracle rerun; original80 frozen gold is reused.
"""
import argparse
import ast
from collections import Counter
import ctypes
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PREPARED = ROOT / 'experiments/r193-mobile-backbone-prepared'
RESULTS = ROOT / 'experiments/r194-mobile-backbone-small'
LARGE = Path(r'G:\Hackathon-stage2-artifacts\project18\r194-mobile-backbone-small')
OLD = ROOT / 'experiments/r185-general-region-functional'
RESERVE, MIN_RAM, MIN_SMALL = 512 * 1024**2, 768 * 1024**2, 64 * 1024**2
PARAMETERS = {'total_ms': 500, 'expansions': 20000, 'transition_attempts': 20000,
              'outlets_each_region': 16, 'mobile_nodes': 32, 'max_regions': 64}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def lines(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        yield from (json.loads(line) for line in stream)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def resources():
    # Reuse OS measurement only, override actual artifact volume explicitly.
    from scripts.research_general_region_isolated import resources as rss
    result = rss()
    result['disk_free_bytes'] = shutil.disk_usage(LARGE.parent).free
    result['output_volume'] = str(LARGE.anchor)
    result['small_report_free_bytes'] = shutil.disk_usage(ROOT).free
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in
            ('total', 'free', 'total_page', 'free_page', 'total_virtual', 'free_virtual', 'free_extended')]
    memory = Memory()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise OSError('Actual free RAM unavailable')
    result['free_RAM_bytes'] = memory.free
    return result


def fanout_fixture():
    """Literal serial construction of one root/40 ADD->SET pairs, not a search."""
    source = [{'id': 0, 'op': 'GET', 'reg': 'shared'}]
    for user in range(40):
        position = len(source)
        source.append({'id': position, 'op': 'ADD', 'inputs': [f't#{position}', f't#{position}']})
        source.append({'id': position + 1, 'op': 'SET', 'reg': f'out{user}', 'inputs': ['t#1']})
    physical = [{'id': 0, 'op': 'GET', 'reg': 'shared'}]
    root_slot, last_add_slot, copies = 0, None, 0
    for index, row in enumerate(source[1:], 1):
        last_root_use = index == 79
        if index <= 79 and not last_root_use and len(physical) - root_slot == 4:
            root_slot = len(physical)
            physical.append({'id': root_slot, 'op': 'COPY', 'source': 't#4'})
            copies += 1
        after = {'id': len(physical), 'op': row['op']}
        if row['op'] == 'ADD':
            after['inputs'] = [f't#{len(physical)-root_slot}'] * 2
            last_add_slot = len(physical)
        else:
            after['reg'] = row['reg']
            after['inputs'] = [f't#{len(physical)-last_add_slot}']
        physical.append(after)
    data = {'block_id': 'mobile-shared-fanout40', 'bit_width': 2, 'instructions': source}
    initial = {'output': {'block_id': data['block_id'], 'optimized_instructions': physical},
               'original_order': list(range(len(source))), 'copies': copies}
    return data, initial


def hazard_fixture():
    rows = [{'id': 0, 'op': 'GET', 'reg': 'a'}, {'id': 1, 'op': 'ADD', 'inputs': ['t#1', 't#1']},
            {'id': 2, 'op': 'SET', 'reg': 'a', 'inputs': ['t#1']}, {'id': 3, 'op': 'GET', 'reg': 'a'},
            {'id': 4, 'op': 'MULW', 'inputs': ['t#1', 't#4']},
            {'id': 5, 'op': 'SET', 'reg': 'out', 'inputs': ['t#1']}]
    data = {'block_id': 'mobile-hazard6', 'bit_width': 2, 'instructions': rows}
    initial = {'output': {'block_id': data['block_id'], 'optimized_instructions': rows},
               'original_order': list(range(6)), 'copies': 0}
    return data, initial


def prepare():
    from isa_scheduler.mobile_backbone_anytime import resource_layout
    if LARGE.exists() or RESULTS.exists():
        raise FileExistsError('New run destination already exists; do not overwrite')
    PREPARED.mkdir(exist_ok=False)
    (PREPARED / 'initials').mkdir()
    (PREPARED / 'gold').mkdir()
    cases = []
    raw80 = ROOT / 'experiments/r184-general-region-functional-prepared/raw80.jsonl'
    for data in lines(raw80):
        key = fingerprint(data)
        initial_path, gold_path = OLD / f'{key[:16]}-initial.json', OLD / f'{key[:16]}-oracle.json'
        initial = load(initial_path)
        gold = load(gold_path)
        shutil.copyfile(initial_path, PREPARED / 'initials' / f'{key}.json')
        shutil.copyfile(gold_path, PREPARED / 'gold' / f'{key}.json')
        cases.append({'kind': 'frozen_tiny80', 'input': data, 'initial_sha256': sha(initial_path),
                      'old_gold_sha256': sha(gold_path), 'old_gold_outcome': gold['outcome'],
                      'old_gold_copies': gold.get('copies'), 'search_mode': 'explicit_all_mobile',
                      'region': {'L': 0, 'R': len(data['instructions']) - 1, 'mobile': list(range(len(data['instructions'])))}})
    assert len(cases) == 80
    hand = load(ROOT / 'research/level-stage/mobile-backbone-hand45.json')
    matrix_key = '06f7a8423ed40df172993cfa526190076a3f5a2a168e901ea1e61459685002bf'
    matrix = next(case['input'] for case in lines(ROOT / 'experiments/r186-general-region-full336-prepared/inputs.jsonl.gz') if fingerprint(case['input']) == matrix_key)
    matrix_initial = next(lines(Path(r'G:\Hackathon-stage2-artifacts\project18\r187-general-region-full336') / f'{matrix_key[:16]}-best.json.gz'))
    extra = [('hand45', hand['input'], hand['baseline']), ('matrix160_saved', matrix, matrix_initial),
             ('hazard6', *hazard_fixture()), ('shared_fanout40', *fanout_fixture())]
    for kind, data, initial in extra:
        key = fingerprint(data)
        write(PREPARED / 'initials' / f'{key}.json', initial)
        case = {'kind': kind, 'input': data, 'search_mode': 'explicit_all_mobile' if kind == 'hazard6' else 'selector_wrapper'}
        if kind == 'hazard6':
            case['region'] = {'L': 0, 'R': 5, 'mobile': list(range(6))}
        cases.append(case)
    assert len(cases) == 84 and len({fingerprint(case['input']) for case in cases}) == 84
    (PREPARED / 'cases.jsonl').write_bytes(b''.join(encoded(case) for case in cases))
    inventories = []
    for case in cases:
        key = fingerprint(case['input'])
        layout = resource_layout(case['input'], load(PREPARED / 'initials' / f'{key}.json'))
        inventories.append({'sha256': key, 'kind': case['kind'], 'layout': layout,
            'package_bytes': layout['diagnostic_bound_bytes'] + 2 * layout['complete_proposal_bound_bytes'] + 64 * 1024**2})
    write(PREPARED / 'resource-layout.json', inventories)
    own = [ROOT / 'isa_scheduler/mobile_backbone_anytime.py', ROOT / 'isa_scheduler/mobile_backbone_refine.py',
           ROOT / 'scripts/raw_mobile_backbone_reference.py', ROOT / 'scripts/mobile_backbone_incremental_replay.py',
           ROOT / 'scripts/audit_mobile_backbone_static.py', ROOT / 'tests/test_mobile_backbone_contracts.py',
           ROOT / 'research/level-stage/mobile-backbone-implementation-contract.md', Path(__file__)]
    prior = [ROOT / 'isa_scheduler/general_region_anytime.py', ROOT / 'isa_scheduler/general_region_refine.py',
             ROOT / 'isa_scheduler/model.py', ROOT / 'isa_scheduler/identity_witness.py',
             ROOT / 'isa_scheduler/verify.py', ROOT / 'scripts/general_region_raw_checks.py',
             ROOT / 'scripts/raw_general_region_oracle.py', ROOT / 'scripts/research_general_region_isolated.py',
             ROOT / 'research/level-stage/mobile-backbone-hand45.json', ROOT / 'research/level-stage/mobile-backbone-next-plan.md']
    entries = {}
    for path in own + prior:
        relative = path.relative_to(ROOT)
        target = PREPARED / 'src' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        entries[relative.as_posix()] = sha(path)
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=str(relative))
    prepared = {str(path.relative_to(PREPARED)).replace('\\', '/'): sha(path)
                for path in PREPARED.rglob('*') if path.is_file() and 'src' not in path.relative_to(PREPARED).parts}
    resource = resources()
    manifest = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': entries,
        'source_aggregate_sha256': hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest(),
        'prepared_sha256': prepared, 'count': 84, 'old_gold_statuses': dict(Counter(case.get('old_gold_outcome') for case in cases[:80])),
        'parameters': PARAMETERS, 'reference_parameters': {'N_max': 9, 'expansions': 20000, 'discovered': 20000, 'transitions': 20000, 'ms': 500},
        'actual_resource_snapshot': resource, 'large_artifact_destination': str(LARGE),
        'large_destination_exists': LARGE.exists(), 'reserve_bytes': RESERVE, 'free_RAM_floor': MIN_RAM, 'small_F_floor': MIN_SMALL,
        'max_input_package_bytes': max(row['package_bytes'] for row in inventories),
        'global_uncompressed_proposal_upper_bytes': sum(1024 * row['layout']['complete_proposal_bound_bytes'] for row in inventories),
        'phase': 'Source-only preparation and literal fixture construction; AST/read/copy/resource prototypes only. No solver/reference/oracle/checker/contracts executed.'}
    write(PREPARED / 'source-provenance.json', manifest)
    print(json.dumps({'prepared': str(PREPARED), 'count': 84, 'source_SHA': manifest['source_aggregate_sha256'],
                      'manifest_SHA': sha(PREPARED / 'source-provenance.json'), 'solver_executed': False}))


def four_check(data, candidate):
    from scripts.general_region_raw_checks import replay
    from scripts.audit_mobile_backbone_static import semantic_check
    from isa_scheduler.verify import verify
    raw = replay(data, candidate['output'], candidate['original_order'])
    if raw['copies'] != candidate['copies']:
        raise AssertionError('Raw COPY count mismatch')
    verify(data, candidate['output'])
    checks = [semantic_check(data, candidate, 'symbolic')]
    for semantics in ((8, True), (16, False), (32, True)):
        for seed in (19001, 19002):
            checks.append(semantic_check(data, candidate, semantics, seed))
    return {'raw_identity_order_hazard': True, 'symbolic': True, 'independent_semantics': checks}


def run():
    from isa_scheduler.mobile_backbone_anytime import search_mobile_backbone, iter_mobile_frontier
    from isa_scheduler.mobile_backbone_refine import refine_mobile_backbones
    from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
    from scripts.raw_mobile_backbone_reference import solve_mobile_raw
    from isa_scheduler.general_region_anytime import RegionStop
    manifest = load(PREPARED / 'source-provenance.json')
    for relative, expected in manifest['source_sha256'].items():
        if sha(ROOT / relative) != expected:
            raise AssertionError('Frozen source changed: ' + relative)
    for relative, expected in manifest['prepared_sha256'].items():
        if sha(PREPARED / relative) != expected:
            raise AssertionError('Frozen input/gold changed: ' + relative)
    RESULTS.mkdir(exist_ok=False)
    LARGE.mkdir(exist_ok=False)
    shutil.copyfile(PREPARED / 'source-provenance.json', RESULTS / 'source-provenance.json')
    records, current = [], None
    packages = {row['sha256']: row['package_bytes'] for row in load(PREPARED / 'resource-layout.json')}
    started = perf_counter()
    try:
        for case in lines(PREPARED / 'cases.jsonl'):
            data = case['input']
            key = fingerprint(data)
            current = key
            initial = load(PREPARED / 'initials' / f'{key}.json')
            before = resources()
            tick = perf_counter()
            if before['disk_free_bytes'] < RESERVE + packages[key] or before['free_RAM_bytes'] < MIN_RAM or before['small_report_free_bytes'] < MIN_SMALL:
                records.append({'sha256': key, 'kind': case['kind'], 'status': 'resource_unknown', 'resources': before,
                                'before_copies': initial['copies'], 'after_copies': initial['copies']})
                write(RESULTS / 'partial-records.json', records)
                continue
            check_start = perf_counter()
            baseline_check = four_check(data, initial)
            verify_seconds = perf_counter() - check_start
            reference = {'outcome': 'not_applicable_N_gt_9'}
            reference_check = None
            if len(data['instructions']) <= 9:
                reference = solve_mobile_raw(data, initial, case['region'], max_states=20000,
                    max_discovered=20000, max_transitions=20000, time_budget_ms=500)
                if reference['candidate'] is not None:
                    reference_check = four_check(data, reference['candidate'])
                if reference['outcome'] == 'closed_neighborhood_infeasible':
                    raise AssertionError('Saved complete initial contradicts raw neighborhood closure')
                if case.get('old_gold_outcome') == 'optimal' and reference['outcome'] == 'optimal_neighborhood':
                    if reference['candidate']['copies'] != case['old_gold_copies']:
                        raise AssertionError('All-mobile raw reference contradicts frozen old global gold')
            write(RESULTS / f'{key[:16]}-reference.json', reference)
            path = LARGE / f'{key[:16]}-complete.jsonl.gz'
            decoded = sink_count = 0
            sink_seconds = 0.0
            with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                def sink(region, candidate):
                    nonlocal decoded, sink_count, sink_seconds
                    clock = perf_counter()
                    blob = encoded({'input_sha256': key, 'region': region, 'candidate': candidate})
                    stream.write(blob)
                    stream.flush()
                    raw.flush()
                    decoded += len(blob)
                    sink_count += 1
                    sink_seconds += perf_counter() - clock
                    actual = resources()
                    if actual['disk_free_bytes'] < RESERVE or actual['free_RAM_bytes'] < MIN_RAM or actual['small_report_free_bytes'] < MIN_SMALL:
                        raise RegionStop('producer_resource_after_saved_complete')
                search_start = perf_counter()
                if case['search_mode'] == 'explicit_all_mobile':
                    result = search_mobile_backbone(data, initial, case['region'], on_completed=lambda candidate: sink(case['region'], candidate))
                    snapshots = [result.pop('diagnostics')]
                else:
                    result = refine_mobile_backbones(data, initial, on_completed=sink, resource_snapshot=resources)
                    snapshots = result.pop('diagnostics')
                search_seconds = perf_counter() - search_start
            check_start = perf_counter()
            for saved in lines(path):
                four_check(data, saved['candidate'])
                if case.get('old_gold_outcome') == 'optimal' and saved['candidate']['copies'] < case['old_gold_copies']:
                    raise AssertionError('Actual candidate below independently frozen optimum')
            four_check(data, result['best'])
            verify_seconds += perf_counter() - check_start
            exports = []
            for index, snapshot in enumerate(snapshots):
                replay = MobilePhysicalReplay(data, initial, snapshot.region)
                target = LARGE / f'{key[:16]}-region{index}-frontier.jsonl.gz'
                export_start = perf_counter()
                count, total, materialize, jsonio, check_time = Counter(), 0, 0.0, 0.0, 0.0
                decoded_sha = hashlib.sha256()
                with target.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                    iterator = iter(iter_mobile_frontier(snapshot))
                    while True:
                        clock = perf_counter()
                        try:
                            record = next(iterator)
                        except StopIteration:
                            materialize += perf_counter() - clock
                            break
                        materialize += perf_counter() - clock
                        clock = perf_counter()
                        blob = encoded(record)
                        limit = 4096 if record['kind'] == 'header' else 2048 if record['kind'] in ('open', 'unfinished_expansion') else 1024
                        if len(blob) > limit:
                            raise AssertionError('Actual cursor diagnostic envelope exceeded')
                        stream.write(blob)
                        total += len(blob)
                        decoded_sha.update(blob)
                        count[record['kind']] += 1
                        jsonio += perf_counter() - clock
                        clock = perf_counter()
                        replay.accept(record)
                        check_time += perf_counter() - clock
                exports.append({'absolute_path': str(target), 'decoded_bytes': total, 'compressed_bytes': target.stat().st_size,
                    'decoded_SHA': decoded_sha.hexdigest(), 'compressed_SHA': sha(target), 'counts': dict(count),
                    'materialize_seconds': materialize, 'JSON_gzip_IO_seconds': jsonio, 'independent_ring_replay_seconds': check_time,
                    'whole_export_seconds': perf_counter() - export_start})
                snapshots[index] = None
                del snapshot, replay
            snapshots.clear()
            best_path = LARGE / f'{key[:16]}-best.json.gz'
            with best_path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                stream.write(encoded(result['best']))
            records.append({'sha256': key, 'kind': case['kind'], 'status': 'verified_initial_fallback',
                'before_copies': initial['copies'], 'after_copies': result['best']['copies'], 'stats': result['stats'],
                'initial_check': baseline_check, 'reference_outcome': reference['outcome'], 'reference_check': reference_check,
                'old_gold_outcome': case.get('old_gold_outcome'), 'actual_complete_outputs': sink_count,
                'complete_path': str(path), 'decoded_complete_bytes': decoded, 'compressed_complete_bytes': path.stat().st_size,
                'compressed_complete_SHA': sha(path), 'best_path': str(best_path), 'best_compressed_SHA': sha(best_path),
                'diagnostic_exports': exports, 'resources_before': before, 'resources_after': resources(),
                'timing_seconds': {'search_emit_including_sink': search_seconds, 'sink_JSON_gzip_IO': sink_seconds,
                                   'four_verify': verify_seconds, 'whole_input': perf_counter() - tick}})
            write(RESULTS / 'partial-records.json', records)
            print(json.dumps({'sha256': key, 'kind': case['kind'], 'before': initial['copies'],
                              'after': result['best']['copies'], 'complete': sink_count}), flush=True)
        write(RESULTS / 'report.json', {'count': len(records), 'records': records, 'elapsed_seconds': perf_counter() - started,
            'scope': 'Original80 frozen tiny + hand45/matrix160/hazard6/fanout40 isolated functional controls; not whole336 or official Level. Prior64 statuses unchanged.'})
    except BaseException as error:
        write(RESULTS / 'failure.json', {'input_sha256': current, 'type': type(error).__name__, 'message': str(error),
                                       'elapsed_seconds': perf_counter() - started, 'automatic_restart': False})
        raise
    evidence = {str(path.relative_to(RESULTS)): sha(path) for path in RESULTS.glob('*') if path.is_file()}
    write(RESULTS / 'evidence-provenance.json', {'source_manifest_SHA': sha(PREPARED / 'source-provenance.json'), 'files': evidence})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument('--prepare', action='store_true')
    choices.add_argument('--run', action='store_true')
    args = parser.parse_args()
    prepare() if args.prepare else run()
