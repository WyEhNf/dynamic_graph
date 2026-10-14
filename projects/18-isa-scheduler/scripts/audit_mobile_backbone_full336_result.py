"""Read-only second replay of saved R196 outputs and all physical frontiers."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.general_region_raw_checks import replay
from scripts.mobile_backbone_semantics import check_semantics
from scripts.mobile_backbone_incremental_replay import MobilePhysicalReplay


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def lines(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream: yield json.loads(line)


def main():
    started = perf_counter()
    results = ROOT / 'experiments/r196-mobile-backbone-full336'
    prepared = ROOT / 'experiments/r195-mobile-backbone-full336-prepared'
    report = json.loads((results / 'report.json').read_text())
    evidence = json.loads((results / 'evidence-provenance.json').read_text())
    for relative, expected in evidence['files'].items():
        assert sha(results / relative) == expected, relative
    inputs = {row['sha256']: row for row in json.loads((prepared / 'inventory.json').read_text())}
    records = {row['sha256']: row for row in report['records']}
    assert len(inputs) == len(records) == 336 and inputs.keys() == records.keys()
    totals, frontier = Counter(), Counter()
    def verify(data, candidate):
        actual = replay(data, candidate['output'], candidate['original_order'])
        assert actual['copies'] == candidate['copies']
        check_semantics(data, candidate)
        totals['whole_outputs_replayed'] += 1
    for case in lines(prepared / 'inputs.jsonl.gz'):
        data = case['input']
        key = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        saved, row = inputs[key], records[key]
        assert row['source_status'] == saved['source_status']
        assert row['before_copies'] == saved['before_copies']
        if saved['initial_absolute_path'] is None:
            assert row['after_copies'] is None
            totals['missing_outputs_preserved'] += 1
            continue
        initial = next(lines(saved['initial_absolute_path']))
        assert sha(saved['initial_absolute_path']) == saved['initial_compressed_SHA']
        verify(data, initial)
        if row.get('best_absolute_path'):
            assert sha(row['best_absolute_path']) == row['best_compressed_SHA']
            best = next(lines(row['best_absolute_path']))
            verify(data, best)
            assert best['copies'] == row['after_copies'] <= initial['copies']
            assert sha(row['complete_absolute_path']) == row['compressed_complete_SHA']
            count = 0
            for proposal in lines(row['complete_absolute_path']):
                assert proposal['input_sha256'] == key
                verify(data, proposal['candidate']); count += 1
            assert count == row['actual_complete_outputs']
            totals['proposals'] += count
            for export in row['diagnostic_exports']:
                assert sha(export['absolute_path']) == export['compressed_SHA']
                checker = None
                actual = Counter()
                for record in lines(export['absolute_path']):
                    if record['kind'] == 'header':
                        checker = MobilePhysicalReplay(data, initial, record['region'])
                    assert checker is not None
                    checker.accept(record); actual[record['kind']] += 1
                assert dict(actual) == export['counts']
                frontier.update(actual)
        else:
            assert row['after_copies'] == initial['copies']
        totals['before_COPY'] += row['before_copies']
        totals['after_COPY'] += row['after_copies']
        totals['improved'] += row['after_copies'] < row['before_copies']
    legal = [row for row in records.values() if row['before_copies'] is not None]
    mean = sum(row['after_copies'] / (row['node_count'] + row['after_copies']) for row in legal) / len(legal)
    summary = report['summary']
    assert totals['before_COPY'] == summary['before_copies'] == 192859
    assert totals['after_COPY'] == summary['after_copies']
    assert totals['improved'] == summary['improved_count']
    assert mean == summary['after_legal_copy_output_mean']
    assert totals['missing_outputs_preserved'] == 64 and summary['all_input_quality_mean'] is None
    result = {'passed': True, 'inputs': len(records), 'legal_outputs': len(legal),
              'totals': dict(totals), 'frontier': dict(frontier),
              'after_legal_copy_output_mean': mean, 'all336_quality_mean': None,
              'elapsed_seconds': perf_counter() - started, 'report_sha256': sha(results / 'report.json'),
              'audit_source_sha256': sha(Path(__file__)), 'default_changed': False,
              'scope': 'Read-only original-identity and physical-ring replay of saved files; no scheduler rerun or official Level claim.'}
    output = ROOT.parents[1] / 'outputs/mobile-backbone-full336-audit-2026-10-12.json'
    with output.open('x', encoding='utf-8') as stream: json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == '__main__': main()
