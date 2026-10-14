"""Verify max-of-bounds join and full retained denominators, not achievable scores."""
import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/18-isa-scheduler'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    path = PROJECT / 'experiments/r143-root-lifetime-summary/report.json'
    report = read(path)
    for name, expected in report['sources_sha256'].items():
        assert sha(PROJECT / name) == expected
    old = {r['sha256']: r for r in read(PROJECT / 'experiments/r99-reduction-global-audit/report.json')['records']}
    roots = {r['sha256']: r for r in read(PROJECT / 'experiments/r134-root-potential-336/report.json')['records']}
    quality = {r['sha256']: r for r in read(PROJECT / 'experiments/r107-age-portfolio-336/report.json')['records']}
    assert len(old) == len(roots) == len(quality) == len(report['records']) == 336
    for row in report['records']:
        key = row['sha256']
        assert row['node_count'] == old[key]['original_nodes'] == quality[key]['node_count']
        assert row['quality_status'] == quality[key]['status']
        assert row['old_lower'] == old[key]['copy_lower_bound']
        assert row['root_lower'] == roots[key]['lower']
        assert row['joint_lower'] == max(row['old_lower'], row['root_lower'])
    summaries = {}
    for label, rows in [('all336_necessary_only', report['records']),
                        ('measured272_necessary_only', [r for r in report['records'] if r['quality_status'] == 'verified'])]:
        observed = dict(count=len(rows), statuses=dict(Counter(r['quality_status'] for r in rows)),
            old_mean_lower_output_pct=100 * statistics.mean(r['old_lower'] / (r['node_count'] + r['old_lower']) for r in rows),
            joint_mean_lower_output_pct=100 * statistics.mean(r['joint_lower'] / (r['node_count'] + r['joint_lower']) for r in rows),
            joint_mean_lower_original_pct=100 * statistics.mean(r['joint_lower'] / r['node_count'] for r in rows),
            lower_improved_inputs=sum(r['joint_lower'] > r['old_lower'] for r in rows))
        for field, value in observed.items():
            expected = report[label][field]
            assert abs(value - expected) < 1e-10 if isinstance(value, float) else value == expected
        summaries[label] = observed
    result = dict(passed=True, reviewed_unix=time.time(), summaries=summaries,
                  evidence={path.relative_to(ROOT).as_posix(): sha(path)},
                  scope='Independent SHA/status/identity join and rational-floor summary denominators over all336 and explicit272 subset. '
                        'Old necessary floors were previously reviewed; new root certificates independently recomputed separately. '
                        'Take maximum, never sum. No actual COPY reduction, achievable optimum, official dataset or Level verdict.')
    (ROOT / 'outputs/stage2-root-bound-join-r143.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
