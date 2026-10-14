"""Read-only post-run evidence index; no scheduler/reference imports or calls."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'experiments/r194-mobile-backbone-small'
PREPARED = ROOT / 'experiments/r193-mobile-backbone-prepared'
LARGE = Path(r'G:\Hackathon-stage2-artifacts\project18\r194-mobile-backbone-small')
LOGS = Path(r'G:\Hackathon-stage2-artifacts\project18\r194-mobile-backbone-contracts')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    manifest = load(PREPARED / 'source-provenance.json')
    for relative, expected in manifest['source_sha256'].items():
        assert sha(ROOT / relative) == expected
        assert sha(PREPARED / 'src' / relative) == expected
    for relative, expected in manifest['prepared_sha256'].items():
        assert sha(PREPARED / relative) == expected
    report = load(RESULTS / 'report.json')
    records = report['records']
    assert len(records) == 84
    files = []
    for path in sorted(LARGE.glob('*.gz')):
        decoded = hashlib.sha256()
        decoded_size = maximum_line = count = 0
        with gzip.open(path, 'rb') as stream:
            for line in stream:
                decoded.update(line)
                decoded_size += len(line)
                maximum_line = max(maximum_line, len(line))
                count += 1
        files.append({'absolute_path': str(path), 'compressed_bytes': path.stat().st_size,
                      'decoded_bytes': decoded_size, 'compressed_SHA': sha(path),
                      'decoded_SHA': decoded.hexdigest(), 'lines': count, 'maximum_line_bytes': maximum_line})
    diagnostics = Counter()
    for record in records:
        for export in record.get('diagnostic_exports', []):
            diagnostics.update(export['counts'])
    timing = Counter()
    for record in records:
        timing.update(record.get('timing_seconds', {}))
    resources = []
    for record in records:
        resources.extend(record.get(name) for name in ('resources_before', 'resources_after') if record.get(name))
        resources.extend(record.get('stats', {}).get('resource_snapshots', []))
    groups = {}
    for kind in dict.fromkeys(record['kind'] for record in records):
        chosen = [record for record in records if record['kind'] == kind]
        groups[kind] = {'count': len(chosen), 'before_COPY': sum(record['before_copies'] for record in chosen),
                       'after_COPY': sum(record['after_copies'] for record in chosen),
                       'improved': sum(record['after_copies'] < record['before_copies'] for record in chosen),
                       'complete_outputs': sum(record.get('actual_complete_outputs', 0) for record in chosen),
                       'outcomes': dict(Counter(record.get('stats', {}).get('outcome') for record in chosen)),
                       'reference_outcomes': dict(Counter(record.get('reference_outcome') for record in chosen))}
    fresh_observed = {'tool_chunk': '74d5da', 'disk_free_bytes': 514760818688,
                      'small_report_free_bytes': 821870592, 'free_RAM_bytes': 6806188032,
                      'output_volume': 'G:\\', 'scope': 'Observed immediately before the actual contract run.'}
    summary = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'phase': 'Read-only evidence indexing; no new solver/reference/oracle or test rerun.',
        'owner_contract_execution': {'tool_chunk': '01f83d', 'exit_code': 0, 'tests': 15, 'unittest_seconds': 0.010,
                                     'actual_log': str(LOGS / 'owner.log'), 'log_SHA': sha(LOGS / 'owner.log')},
        'owner_84_execution': {'tool_chunk': '6337d3', 'exit_code': 0, 'session_created': False,
                              'command_wall_seconds': 7.4312917, 'actual_log': str(LOGS / 'batch-owner.log'),
                              'log_SHA': sha(LOGS / 'batch-owner.log'), 'process_liveness': 'Actual command returned terminal exit0; no live exec handle.'},
        'fresh_resource_snapshot': fresh_observed, 'groups': groups, 'count': len(records),
        'statuses': dict(Counter(record['status'] for record in records)),
        'before_COPY': sum(record['before_copies'] for record in records), 'after_COPY': sum(record['after_copies'] for record in records),
        'complete_outputs': sum(record.get('actual_complete_outputs', 0) for record in records),
        'saved_initial_and_best': 168,
        'raw_reference_complete_candidates': sum(record.get('reference_check') is not None for record in records),
        'whole_four_checked_outputs': 168 + sum(record.get('actual_complete_outputs', 0) for record in records) + sum(record.get('reference_check') is not None for record in records),
        'diagnostic_counts': dict(diagnostics), 'timing_seconds': dict(timing),
        'whole_report_elapsed_seconds': report['elapsed_seconds'],
        'measured_process_lifetime_peak_RSS_bytes': max(sample['process_peak_working_set_bytes'] for sample in resources),
        'sampled_current_input_RSS_max_bytes': max(sample['working_set_bytes'] for sample in resources),
        'minimum_sampled_G_free_bytes': min(sample['disk_free_bytes'] for sample in resources),
        'minimum_sampled_F_small_bytes': min(sample['small_report_free_bytes'] for sample in resources),
        'minimum_sampled_free_RAM_bytes': min(sample['free_RAM_bytes'] for sample in resources),
        'gzip_file_count': len(files), 'compressed_total_bytes': sum(file['compressed_bytes'] for file in files),
        'decoded_total_bytes': sum(file['decoded_bytes'] for file in files),
        'source_manifest_SHA': sha(PREPARED / 'source-provenance.json'), 'source_aggregate_SHA': manifest['source_aggregate_sha256'],
        'report_SHA': sha(RESULTS / 'report.json'), 'producer_evidence_SHA': sha(RESULTS / 'evidence-provenance.json'),
        'scope': '84 isolated functional controls, not original336/official Level or an isolated speed comparison. Matrix gain single best proposal, not accumulated neighborhoods. Original64 statuses and default unchanged.',
        'files': files}
    with (RESULTS / 'artifact-provenance.json').open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    copied = RESULTS / 'post-run-source'
    copied.mkdir(exist_ok=False)
    shutil.copyfile(Path(__file__), copied / Path(__file__).name)
    with (RESULTS / 'post-run-manifest.json').open('x', encoding='utf-8') as stream:
        json.dump({'frozen_utc': datetime.now(timezone.utc).isoformat(), 'static_indexer_SHA': sha(Path(__file__)),
                   'artifact_provenance_SHA': sha(RESULTS / 'artifact-provenance.json'),
                   'producer_source_manifest_SHA': summary['source_manifest_SHA'],
                   'producer_evidence_SHA': summary['producer_evidence_SHA']}, stream, indent=2)
    print(json.dumps({key: summary[key] for key in ('count', 'groups', 'before_COPY', 'after_COPY', 'complete_outputs',
        'whole_four_checked_outputs', 'diagnostic_counts', 'whole_report_elapsed_seconds', 'measured_process_lifetime_peak_RSS_bytes',
        'gzip_file_count', 'compressed_total_bytes', 'decoded_total_bytes', 'report_SHA', 'source_manifest_SHA')}, ensure_ascii=False))
    print(json.dumps({'artifact_provenance_SHA': sha(RESULTS / 'artifact-provenance.json'), 'post_run_manifest_SHA': sha(RESULTS / 'post-run-manifest.json')}))


if __name__ == '__main__':
    main()
