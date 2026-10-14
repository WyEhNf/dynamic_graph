"""R195 source/linked-incumbent freeze; future R196 full original336 run.

Preparation never schedules/verifies/evaluates or calls an oracle. Every legal
incumbent is exactly R187's accepted best (or its unchanged zero-copy source).
Actual --run is a separate parent gate, not executed by preparing this file.
"""
import argparse
import ast
from collections import Counter
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
SOURCE = ROOT / 'experiments/r187-general-region-full336'
SOURCE_PREPARED = ROOT / 'experiments/r186-general-region-full336-prepared'
SOURCE_LARGE = Path(r'G:\Hackathon-stage2-artifacts\project18\r187-general-region-full336')
PREPARED = ROOT / 'experiments/r195-mobile-backbone-full336-prepared'
RESULTS = ROOT / 'experiments/r196-mobile-backbone-full336'
LARGE = Path(r'G:\Hackathon-stage2-artifacts\project18\r196-mobile-backbone-full336')
RESERVE, MIN_RAM, MIN_SMALL = 512 * 1024**2, 768 * 1024**2, 64 * 1024**2
PARAMETERS = {'total_ms': 500, 'expansions': 20000, 'transition_attempts': 20000,
              'outlets_each_region': 16, 'mobile_nodes': 32, 'max_regions': 64}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def decoded_sha(path):
    digest = hashlib.sha256()
    with gzip.open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def lines(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        yield from (json.loads(line) for line in stream)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def resources():
    from scripts.research_mobile_backbone_small import resources as measured
    result = measured()
    result['disk_free_bytes'] = shutil.disk_usage(LARGE.parent).free
    result['output_volume'] = LARGE.anchor
    return result


def prepare():
    from isa_scheduler.mobile_backbone_anytime import resource_layout
    if RESULTS.exists() or LARGE.exists():
        raise FileExistsError('New R196 destination already exists')
    PREPARED.mkdir(exist_ok=False)
    frozen = load(SOURCE / 'source-provenance.json')
    # Preserve/validate the full original R188 source bank, not a shortened list.
    for relative, expected in frozen['source_sha256'].items():
        if sha(ROOT / relative) != expected:
            raise AssertionError('R187 source changed: ' + relative)
    report = load(SOURCE / 'report.json')
    old = {row['sha256']: row for row in report['records']}
    if len(old) != 336:
        raise AssertionError('Original full336 is required')
    expected_status = Counter({'verified': 272, 'proven_infeasible_under_model': 47, 'budget_exhausted': 9, 'scheduling_failure': 8})
    if Counter(row['source_status'] for row in old.values()) != expected_status:
        raise AssertionError('Historical statuses changed')
    shutil.copyfile(SOURCE_PREPARED / 'inputs.jsonl.gz', PREPARED / 'inputs.jsonl.gz')
    inventory = []
    for case in lines(PREPARED / 'inputs.jsonl.gz'):
        data = case['input']
        key = fingerprint(data)
        saved = old[key]
        initial_path = None
        initial = layout = None
        if saved['after_copies'] is not None:
            initial_path = SOURCE_LARGE / f'{key[:16]}-best.json.gz'
            if not initial_path.exists():
                initial_path = SOURCE_PREPARED / 'initials' / f'{key}.json.gz'
            initial = next(lines(initial_path))
            if initial['copies'] != saved['after_copies']:
                raise AssertionError('Current R187 accepted incumbent mismatch')
            layout = resource_layout(data, initial)
        package = None if layout is None else layout['diagnostic_bound_bytes'] + 2 * layout['complete_proposal_bound_bytes'] + 64 * 1024**2
        inventory.append({'sha256': key, 'family': case['family'], 'node_count': len(data['instructions']),
            'bit_width': data['bit_width'], 'source_status': saved['source_status'], 'before_copies': saved['after_copies'],
            'prior_candidate_outcome': saved['candidate_outcome'],
            'historical_failure_or_certificate': saved.get('historical_failure_or_certificate'),
            'initial_absolute_path': None if initial_path is None else str(initial_path),
            'initial_compressed_SHA': None if initial_path is None else sha(initial_path),
            'initial_decoded_SHA': None if initial_path is None else decoded_sha(initial_path),
            'resource_layout': layout, 'input_package_bytes': package,
            'route': 'no_incumbent_preserved' if initial is None else 'zero_copy_retained' if initial['copies'] == 0 else 'mobile_backbone_search'})
    if len(inventory) != 336 or {row['sha256'] for row in inventory} != set(old):
        raise AssertionError('Input/full status join changed')
    if sum(row['before_copies'] or 0 for row in inventory) != 192859:
        raise AssertionError('Original R187 fixed272 initial quality changed')
    write(PREPARED / 'inventory.json', inventory)
    paths = list((ROOT / 'isa_scheduler').glob('*.py')) + [Path(__file__),
        ROOT / 'scripts/mobile_backbone_incremental_replay.py', ROOT / 'scripts/mobile_backbone_semantics.py',
        ROOT / 'scripts/general_region_raw_checks.py', ROOT / 'scripts/raw_general_region_oracle.py',
        ROOT / 'scripts/research_mobile_backbone_small.py', ROOT / 'scripts/research_general_region_isolated.py',
        ROOT / 'tests/test_mobile_backbone_contracts.py', ROOT / 'tests/test_mobile_backbone_semantics.py',
        ROOT / 'research/level-stage/mobile-backbone-full336-runner.md']
    source_hashes = {}
    for path in paths:
        relative = path.relative_to(ROOT)
        target = PREPARED / 'src' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        source_hashes[relative.as_posix()] = sha(path)
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=str(relative))
    resources_plan = {'actual_preparation': resources(), 'reserve_bytes': RESERVE, 'minimum_free_RAM': MIN_RAM,
        'minimum_F_small': MIN_SMALL, 'actual_large_target_exists': LARGE.exists(), 'large_target': str(LARGE),
        'maximum_input_package_bytes': max(row['input_package_bytes'] or 0 for row in inventory),
        'maximum_complete_proposal_bytes': max(row['resource_layout']['complete_proposal_bound_bytes'] if row['resource_layout'] else 0 for row in inventory),
        'global_uncompressed_proposal_upper_bytes': sum(1024 * row['resource_layout']['complete_proposal_bound_bytes'] for row in inventory if row['route'] == 'mobile_backbone_search'),
        'global_diagnostic_upper_bytes': sum(row['resource_layout']['diagnostic_bound_bytes'] for row in inventory if row['route'] == 'mobile_backbone_search'),
        'scope': 'Actual input UTF8+F+NW bounds, no assumed gzip ratio/RSS upper estimate. Complete streams and all diagnostics saved; reserve stops tail unknown, no deletion/sampling/restart.'}
    write(PREPARED / 'resource-plan.json', resources_plan)
    provenance = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': source_hashes,
        'source_aggregate_SHA': hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest(),
        'prepared_sha256': {name: sha(PREPARED / name) for name in ('inputs.jsonl.gz', 'inventory.json', 'resource-plan.json')},
        'historical_R187_source_manifest_SHA': sha(SOURCE / 'source-provenance.json'), 'historical_R187_report_SHA': sha(SOURCE / 'report.json'),
        'historical_R187_evidence_SHA': sha(SOURCE / 'evidence-provenance.json'),
        'historical_full_source_files_sha256': frozen['source_sha256'],
        'count': 336, 'families': 21, 'legal_initial_count': 272, 'initial_COPY': 192859,
        'status_counts': dict(expected_status), 'parameters': PARAMETERS,
        'source_r193_manifest_SHA': sha(ROOT / 'experiments/r193-mobile-backbone-prepared/source-provenance.json'),
        'r194_actual_report_SHA': sha(ROOT / 'experiments/r194-mobile-backbone-small/report.json'),
        'phase': 'Source-only prepared metadata/layouts+linked priorG/Fbank SHA; no solver/reference/oracle/test/verification execution.'}
    write(PREPARED / 'source-provenance.json', provenance)
    print(json.dumps({'prepared': str(PREPARED), 'source_SHA': provenance['source_aggregate_SHA'],
        'manifest_SHA': sha(PREPARED / 'source-provenance.json'), 'routes': dict(Counter(row['route'] for row in inventory)),
        'resources': resources_plan, 'solver_executed': False}))


def four_check(data, candidate):
    from scripts.general_region_raw_checks import replay
    from scripts.mobile_backbone_semantics import check_semantics
    from isa_scheduler.verify import verify
    observed = replay(data, candidate['output'], candidate['original_order'])
    if observed['copies'] != candidate['copies']:
        raise AssertionError('Independent raw original identity COPY statistic mismatch')
    verify(data, candidate['output'])
    independent = check_semantics(data, candidate)
    return {'raw_identity_order_hazard': True, 'symbolic_verify': True,
            'independent_flat_symbols_and_local_integers': independent, 'copies': observed['copies']}


def summarize(records):
    legal = [row for row in records if row['before_copies'] is not None]
    result = {'count': len(records), 'legal_initial_count': len(legal),
        'source_statuses': dict(Counter(row['source_status'] for row in records)),
        'candidate_outcomes': dict(Counter(row['candidate_outcome'] for row in records)),
        'before_copies': sum(row['before_copies'] for row in legal), 'after_copies': sum(row['after_copies'] for row in legal),
        'improved_count': sum(row['after_copies'] < row['before_copies'] for row in legal),
        'actual_complete_outputs': sum(row.get('actual_complete_outputs', 0) for row in records),
        'all_input_quality_mean': None, 'all_input_quality_mean_reason': 'All original64 no-incumbent statuses retained; never imputed zero or excluded from full336 state totals.'}
    for prefix in ('before', 'after'):
        result[prefix + '_legal_copy_output_mean'] = sum(row[prefix + '_copies'] / (row['node_count'] + row[prefix + '_copies']) for row in legal) / len(legal) if legal else None
        result[prefix + '_legal_copy_original_mean'] = sum(row[prefix + '_copies'] / row['node_count'] for row in legal) / len(legal) if legal else None
    return result


def run():
    from isa_scheduler.mobile_backbone_refine import refine_mobile_backbones
    from isa_scheduler.mobile_backbone_anytime import iter_mobile_frontier
    from isa_scheduler.general_region_anytime import RegionStop
    from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay
    manifest = load(PREPARED / 'source-provenance.json')
    for relative, expected in manifest['source_sha256'].items():
        if sha(ROOT / relative) != expected:
            raise AssertionError('New source changed: ' + relative)
    for relative, expected in manifest['historical_full_source_files_sha256'].items():
        if sha(ROOT / relative) != expected:
            raise AssertionError('R187 historical source changed: ' + relative)
    for name, expected in manifest['prepared_sha256'].items():
        if sha(PREPARED / name) != expected:
            raise AssertionError('Frozen cases/layouts changed: ' + name)
    if sha(SOURCE / 'report.json') != manifest['historical_R187_report_SHA'] or sha(SOURCE / 'source-provenance.json') != manifest['historical_R187_source_manifest_SHA']:
        raise AssertionError('Historical R187 report/source manifest changed')
    inventory = {row['sha256']: row for row in load(PREPARED / 'inventory.json')}
    for row in inventory.values():
        if row['initial_absolute_path'] is not None:
            path = Path(row['initial_absolute_path'])
            if sha(path) != row['initial_compressed_SHA'] or decoded_sha(path) != row['initial_decoded_SHA']:
                raise AssertionError('Linked R187 accepted initial changed')
    if RESULTS.exists() or LARGE.exists():
        raise FileExistsError('Cannot overwrite a prior attempt')
    RESULTS.mkdir(exist_ok=False)
    LARGE.mkdir(exist_ok=False)
    shutil.copyfile(PREPARED / 'source-provenance.json', RESULTS / 'source-provenance.json')
    records, baseline_checks, halt = [], {}, None
    started, current = perf_counter(), None
    timings = Counter()
    def gate(snapshot, package):
        if snapshot['disk_free_bytes'] < RESERVE + package:
            return 'G_output_reserve'
        if snapshot['small_report_free_bytes'] < MIN_SMALL:
            return 'F_small_reserve'
        if snapshot['free_RAM_bytes'] < MIN_RAM:
            return 'free_RAM_floor'
        return None
    try:
        # Validate saved full outputs once, never call their scheduler/baseline.
        for case in lines(PREPARED / 'inputs.jsonl.gz'):
            key = fingerprint(case['input'])
            source = inventory[key]
            if source['initial_absolute_path'] is None:
                continue
            current = key
            snapshot = resources()
            if halt is None:
                halt = gate(snapshot, source['input_package_bytes'])
            if halt is not None:
                continue
            initial = next(lines(Path(source['initial_absolute_path'])))
            tick = perf_counter()
            baseline_checks[key] = four_check(case['input'], initial)
            timings['initial_four_verify'] += perf_counter() - tick
            del initial
        write(RESULTS / 'baseline-checks.json', baseline_checks)
        for case in lines(PREPARED / 'inputs.jsonl.gz'):
            data = case['input']
            key = fingerprint(data)
            current = key
            source = inventory[key]
            record = {name: source[name] for name in ('sha256', 'family', 'node_count', 'bit_width', 'source_status', 'before_copies', 'historical_failure_or_certificate')}
            record.update(after_copies=source['before_copies'], actual_complete_outputs=0,
                          baseline_check=baseline_checks.get(key), accepted_initial_absolute_path=source['initial_absolute_path'])
            before = resources()
            record['resources_before'] = before
            if source['route'] == 'no_incumbent_preserved':
                record['candidate_outcome'] = 'no_incumbent_' + source['source_status']
            elif halt is not None:
                record['candidate_outcome'] = 'resource_tail_unknown_' + halt
            elif source['route'] == 'zero_copy_retained':
                record['candidate_outcome'] = 'verified_zero_copy_retained'
            else:
                halt = gate(before, source['input_package_bytes'])
                if halt is not None:
                    record['candidate_outcome'] = 'resource_tail_unknown_' + halt
                else:
                    initial = next(lines(Path(source['initial_absolute_path'])))
                    path = LARGE / f'{key[:16]}-complete.jsonl.gz'
                    decoded_size = sink_count = 0
                    decoded_digest = hashlib.sha256()
                    sink_seconds = 0.0
                    with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                        def sink(region, candidate):
                            nonlocal decoded_size, sink_count, sink_seconds
                            tick = perf_counter()
                            blob = encoded({'input_sha256': key, 'region_index': region, 'candidate': candidate})
                            stream.write(blob)
                            stream.flush()
                            raw.flush()
                            decoded_digest.update(blob)
                            decoded_size += len(blob)
                            sink_count += 1
                            sink_seconds += perf_counter() - tick
                            snapshot = resources()
                            if gate(snapshot, 0) is not None:
                                raise RegionStop('producer_resource_after_saved_complete')
                        tick = perf_counter()
                        result = refine_mobile_backbones(data, initial, on_completed=sink, resource_snapshot=resources)
                        search_seconds = perf_counter() - tick
                    timings['search_emit_including_sink'] += search_seconds
                    timings['sink_gzip_JSON_IO'] += sink_seconds
                    # Complete outputs are actual whole proposals; all saved,
                    # including worse/nonwinning/last proposal before interrupt.
                    tick = perf_counter()
                    for proposed in lines(path):
                        four_check(data, proposed['candidate'])
                    four_check(data, result['best'])
                    verify_seconds = perf_counter() - tick
                    timings['proposal_and_best_four_verify'] += verify_seconds
                    exports = []
                    snapshots = result.pop('diagnostics')
                    for index, snapshot in enumerate(snapshots):
                        replay = MobilePhysicalReplay(data, initial, snapshot.region)
                        target = LARGE / f'{key[:16]}-region{index}-frontier.jsonl.gz'
                        counts = Counter()
                        decoded = hashlib.sha256()
                        total = 0
                        materialize = jsonio = rawcheck = 0.0
                        export_start = perf_counter()
                        with target.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                            iterator = iter(iter_mobile_frontier(snapshot))
                            while True:
                                tick = perf_counter()
                                try:
                                    view = next(iterator)
                                except StopIteration:
                                    materialize += perf_counter() - tick
                                    break
                                materialize += perf_counter() - tick
                                tick = perf_counter()
                                blob = encoded(view)
                                cap = 4096 if view['kind'] == 'header' else 2048 if view['kind'] in ('open', 'unfinished_expansion') else 1024
                                if len(blob) > cap:
                                    raise AssertionError('Actual cursor/roles serialized envelope exceeded')
                                stream.write(blob)
                                total += len(blob)
                                decoded.update(blob)
                                counts[view['kind']] += 1
                                jsonio += perf_counter() - tick
                                tick = perf_counter()
                                replay.accept(view)
                                rawcheck += perf_counter() - tick
                        exports.append({'absolute_path': str(target), 'counts': dict(counts), 'decoded_bytes': total,
                            'compressed_bytes': target.stat().st_size, 'decoded_SHA': decoded.hexdigest(), 'compressed_SHA': sha(target),
                            'materialize_seconds': materialize, 'gzip_JSON_IO_seconds': jsonio,
                            'independent_ring_replay_seconds': rawcheck, 'whole_export_seconds': perf_counter() - export_start})
                        snapshots[index] = None
                        del snapshot, replay
                    snapshots.clear()
                    timings['diagnostic_whole_export'] += sum(export['whole_export_seconds'] for export in exports)
                    best_path = LARGE / f'{key[:16]}-best.json.gz'
                    best_blob = encoded(result['best'])
                    with best_path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                        stream.write(best_blob)
                    record.update(after_copies=result['best']['copies'], candidate_outcome=result['stats']['outcome'],
                        stats=result['stats'], actual_complete_outputs=sink_count, complete_absolute_path=str(path),
                        decoded_complete_bytes=decoded_size, compressed_complete_bytes=path.stat().st_size,
                        decoded_complete_SHA=decoded_digest.hexdigest(), compressed_complete_SHA=sha(path),
                        best_absolute_path=str(best_path), best_decoded_SHA=hashlib.sha256(best_blob).hexdigest(), best_compressed_SHA=sha(best_path),
                        diagnostic_exports=exports, timing_seconds={'search_emit_including_sink': search_seconds,
                            'sink_gzip_JSON_IO': sink_seconds, 'proposal_and_best_four_verify': verify_seconds})
                    del result, initial
                    # Any resource stop preserves that last complete output and
                    # initial fallback; the unexecuted tail stays unknown.
                    after = resources()
                    if 'resource' in record['candidate_outcome']:
                        halt = 'producer_or_wrapper_resource_stop'
                    elif gate(after, 0) is not None:
                        halt = gate(after, 0)
            record['resources_after'] = resources()
            records.append(record)
            write(RESULTS / 'partial-records.json', records)
            print(json.dumps({'sha256': key, 'source': record['source_status'], 'candidate': record['candidate_outcome'],
                              'before': record['before_copies'], 'after': record['after_copies'], 'complete': record['actual_complete_outputs']}), flush=True)
        family = {name: summarize([row for row in records if row['family'] == name]) for name in dict.fromkeys(row['family'] for row in records)}
        write(RESULTS / 'report.json', {'summary': summarize(records), 'families': family, 'records': records,
            'verified_initial_count': len(baseline_checks), 'elapsed_seconds': perf_counter() - started,
            'timing_seconds': dict(timings), 'source_manifest_SHA': sha(PREPARED / 'source-provenance.json'),
            'scope': 'Fixed original336/21families and R187272 initials+64 prior statuses. Every neighborhood same initial, no composed gains; local necessary bounds unchanged, no official Level/default claim.'})
    except BaseException as error:
        write(RESULTS / 'failure.json', {'input_sha256': current, 'type': type(error).__name__, 'message': str(error),
            'completed_records': len(records), 'elapsed_seconds': perf_counter() - started, 'automatic_restart': False})
        raise
    evidence = {str(path.relative_to(RESULTS)): sha(path) for path in RESULTS.glob('*') if path.is_file()}
    write(RESULTS / 'evidence-provenance.json', {'source_manifest_SHA': sha(PREPARED / 'source-provenance.json'), 'files': evidence})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--run', action='store_true')
    options = parser.parse_args()
    prepare() if options.prepare else run()
