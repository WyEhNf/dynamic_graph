"""Independent root audit of the actual installed-default paired experiment."""
import json
import statistics
import time
from pathlib import Path
from review_stage2_vm_threaded_measurements import sha, compare_files, check_repeat
from review_stage2_vm_production_plan import headers

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/19-dynamic-graph'
F = P/'artifacts/stage2-vm-default-integration/production-performance'


def main():
    plan = json.loads((F/'run-plan.json').read_text())
    report = json.loads((F/'report.json').read_text())
    manifest = json.loads((F/'final-manifest.json').read_text())
    assert report['passed'] and report['status'] == 'complete'
    assert sha(F/'run-plan.json') == report['plan_sha256'] == '808f6a035f036d83b9b7f48cee327a388af30cc25c2e9620e15a5da23cbde6c6'
    assert manifest['passed'] and manifest['actual_exit_code'] == 0 and manifest['actual_session'] == 80050
    assert manifest['plan_sha256'] == report['plan_sha256']
    assert manifest['report_sha256'] == sha(F/'report.json')
    assert manifest['summary_sha256'] == sha(F/'summary-audit.json')
    assert manifest['source_snapshot_sha256'] == plan['source_snapshot_sha256']
    assert manifest['actual_binaries'] == plan['binaries']
    for name, digest in manifest['final_evidence_source_sha256'].items():
        assert sha(F/'final-evidence-source'/name) == digest
    assert sha(F/'benchmark-script.py') == plan['script_sha256']
    assert sha(F/'windows_resource_probe.py') == plan['resource_probe_sha256']
    for name, digest in plan['source_snapshot_sha256'].items():
        assert sha(F/'source-frozen'/name) == digest
    for backend, binary in plan['binaries'].items():
        assert sha(Path(binary['path'])) == binary['sha256']
    assert sha(P/'build/cholesky_runtime.exe') == plan['binaries']['new-default']['sha256']
    rows = report['records']
    records = {(r['source'], r['round'], r['backend']): r for r in rows}
    assert len(records) == len(rows) == 130
    expected_order = []
    for round in range(5):
        cases = plan['cases'][round:]+plan['cases'][:round]
        backends = ('old-default', 'new-default') if round % 2 == 0 else ('new-default', 'old-default')
        expected_order.extend((c['source'], round, b) for c in cases for b in backends)
    assert [(r['source'], r['round'], r['backend']) for r in rows] == expected_order
    original_runs = json.loads((P/'artifacts/stage2-prepared-vm-phase3/correctness/report.json').read_text())['runs']
    summaries, pairs = [], []
    for case in plan['cases']:
        folder = F/case['source']
        for name, digest in case['hashes'].items():
            assert sha(folder/name) == digest
        assert headers(folder/'input.bin') == headers(folder/'oracle.bin') == case['input_matrix_headers']
        original = next(r for r in original_runs if r['source'] == case['source'] and r['family'] == 'dense')
        check_repeat(Path(original['input']), folder/'input.bin', case['whole_stream_repeats'])
        check_repeat(Path(original['reference']), folder/'oracle.bin', case['whole_stream_repeats'])
        ratios, walls, new_rows, old_rows = [], [], [], []
        for round in range(5):
            pair = [records[case['source'], round, b] for b in ('old-default', 'new-default')]
            for row in pair:
                backend = row['backend']
                raw = json.loads((folder/f'round-{round}-{backend}.stdout').read_text())
                assert (folder/f'round-{round}-{backend}.stderr').read_text() == ''
                assert row['actual_exit_code'] == 0 and all(row[k] == v for k, v in raw.items())
                assert row['command'] == [plan['binaries'][backend]['path'], '--metadata', str(folder/'program.meta'),
                                          '--input', str(folder/'input.bin'), '--output', str(folder/f'round-{round}-{backend}.bin'),
                                          '--engine', 'auto', '--threads', '4']
                assert row['selected_engine'] == 'vm' and row['matrices'] == case['matrices']
                assert row['exe_sha256'] == plan['binaries'][backend]['sha256']
                assert row['source_sha256'] == case['hashes']['source.c']
                assert row['input_sha256'] == case['hashes']['input.bin']
                assert row['metadata_sha256'] == case['hashes']['program.meta']
                assert row['reference_sha256'] == case['hashes']['oracle.bin']
                assert row['resource_samples'] > 0 and 0 <= row['host_busy_percent_during_process'] <= 100
                assert 0 < row['host_available_ram_min_bytes'] <= row['host_ram_bytes']
                assert row['process_peak_working_set_bytes'] > 0 and row['process_peak_commit_bytes'] > 0
                for field in ('sha_validation_ms', 'whole_file_comparison_ms', 'process_wall_ms', 'input_read_ms', 'output_write_ms', 'compute_ms'):
                    assert row[field] >= 0
                size, hashes = compare_files([folder/'oracle.bin', Path(row['output'])])
                assert size == row['bytes'] and hashes[0] == hashes[1] == row['sha256'] == row['reference_sha256']
                if backend == 'old-default':
                    assert not any(k in raw or k in row for k in ('vm_steps', 'vm_backend', 'vm_prepare_ms', 'vm_plan_bytes_peak'))
                else:
                    assert row['vm_backend'] == 'decoded-threaded' and row['vm_steps'] == case['expected_new_reported_steps']
                    assert 0 <= row['vm_prepare_ms'] <= row['compute_ms']
            old, new = pair
            ratio = new['compute_ms']/old['compute_ms']
            wall = new['process_wall_ms']/old['process_wall_ms']
            ratios.append(ratio); walls.append(wall); old_rows.append(old); new_rows.append(new)
            pairs.append(dict(source=case['source'], round=round, compute_ratio_new_over_old=ratio,
                              wall_ratio_new_over_old=wall, compute_outcome='win' if ratio < 1 else 'tie' if ratio == 1 else 'negative'))
        summary = next(r for r in report['summary'] if r['source'] == case['source'])
        assert ratios == summary['paired_compute_ratios'] and walls == summary['paired_wall_ratios']
        assert statistics.median(ratios) == summary['median_paired_ratio']
        assert statistics.median(walls) == summary['median_paired_wall_ratio']
        assert statistics.median(r['compute_ms'] for r in old_rows) == summary['old_default_median_compute_ms']
        assert statistics.median(r['compute_ms'] for r in new_rows) == summary['new_default_median_compute_ms']
        assert sum(x < 1 for x in ratios) == summary['new_default_compute_wins']
        assert sum(x > 1 for x in ratios) == summary['new_default_compute_negatives']
        summaries.append(dict(source=case['source'], median_paired_ratio=statistics.median(ratios),
                              median_paired_wall_ratio=statistics.median(walls), negative_pairs=sum(x > 1 for x in ratios)))
    assert len(pairs) == 65 and pairs == report['pairs']
    negatives = [p for p in pairs if p['compute_outcome'] == 'negative']
    assert negatives == report['negative_pairs']
    wins = sum(p['compute_outcome'] == 'win' for p in pairs)
    ties = sum(p['compute_outcome'] == 'tie' for p in pairs)
    assert wins == report['wins'] and ties == report['ties']
    result = dict(passed=True, reviewed_unix=time.time(), performance_records=130, paired_comparisons=65,
                  actual_old_sha256=plan['binaries']['old-default']['sha256'],
                  actual_new_sha256=plan['binaries']['new-default']['sha256'], wins=wins,
                  negative_pairs=len(negatives), ties=ties, summaries=summaries,
                  host_busy_percent_range=[min(r['host_busy_percent_during_process'] for r in rows), max(r['host_busy_percent_during_process'] for r in rows)],
                  host_free_ram_min_bytes=min(r['host_available_ram_min_bytes'] for r in rows),
                  working_set_peak_bytes=max(r['process_peak_working_set_bytes'] for r in rows),
                  commit_peak_bytes=max(r['process_peak_commit_bytes'] for r in rows),
                  final_frozen_evidence_files=len(manifest['final_evidence_source_sha256']),
                  evidence={x.relative_to(ROOT).as_posix(): sha(x) for x in (F/'run-plan.json', F/'report.json', F/'final-manifest.json', F/'summary-audit.json')},
                  scope='Root checked all 130 complete real-C output files, raw stdout/stderr, original cached stream repetitions including every M/N header, immutable sources/binaries, trial ordering and all 65 ratios. Actual99a default versus old4f73 default, reused13-source local cohort, default budgets unchanged. Preparation included in compute, host background recorded. No new holdout/general-C/native/official-score claim.')
    (ROOT/'outputs/stage2-root-vm-production-measurements.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
