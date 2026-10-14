"""Schema-compatible all-record summarizer with exact per-trial host provenance.

No benchmarks are started here. Both CPU ratio medians are retained separately.
"""
import hashlib
import json
from pathlib import Path
from host_sampler_batch51 import cpu_delta

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
plan = json.loads(Path('research/batch51/paired-plan.json').read_text(encoding='utf-8'))
driver = json.loads(Path('research/batch51/paired-driver-status.json').read_text(encoding='utf-8'))
assert driver['plan_sha'] == sha('research/batch51/paired-plan.json')
assert len(driver['statuses']) == 2 and all(row['actual_exit_code'] == 0 for row in driver['statuses'])
for path, expected in plan['scripts'].items():
    assert sha(path) == expected, path


def verify_host(meta):
    path = Path(meta['host_report'])
    assert sha(path) == meta['host_report_sha256'], path
    host = json.loads(path.read_text(encoding='utf-8'))
    assert host == meta['host_load']
    samples = host['samples']
    assert len(samples) >= 2
    assert host['trial_cpu_delta'] == cpu_delta(samples[0]['cpu_ticks'], samples[-1]['cpu_ticks'])
    for row, first, last in zip(host['cpu_intervals'], samples, samples[1:]):
        assert row['delta'] == cpu_delta(first['cpu_ticks'], last['cpu_ticks'])
        assert row['begin_seconds'] == first['elapsed_seconds'] and row['end_seconds'] == last['elapsed_seconds']
    memories = [row['memory'] for row in samples if row['memory'] is not None]
    if memories:
        assert host['available_physical_bytes_start'] == memories[0]['available_physical_bytes']
        assert host['available_physical_bytes_end'] == memories[-1]['available_physical_bytes']
        assert host['available_physical_bytes_min'] == min(row['available_physical_bytes'] for row in memories)
    return dict(report=str(path), report_sha=sha(path), status=host['status'],
                trial_cpu_delta=host['trial_cpu_delta'], sample_count=len(samples),
                available_physical_bytes_start=host['available_physical_bytes_start'],
                available_physical_bytes_end=host['available_physical_bytes_end'],
                available_physical_bytes_min=host['available_physical_bytes_min'],
                errors=host['errors'], logical_processors=host['logical_processors'],
                processor_scope=host['processor_scope'])


for family in ('hard', 'heldout'):
    summary = json.loads(Path(f'reports/paired-{family}-batch51-summary.json').read_text(encoding='utf-8'))
    assert summary['baseline_exe_sha256'] == plan['baseline_exe']
    assert summary['current_exe_sha256'] == plan['candidate_exe']
    assert summary['current_solution_sha256'] == plan['candidate_source']
    assert summary['suite_sha256'] == plan['datasets'][Path(summary['suite']).as_posix()]
    assert len(summary['runs']) == 3
    for row in summary['runs']:
        for side in ('before', 'after'):
            verify_host(row[side])

# Preserve previously independently audited R45 grouping/median schema; only
# update batch paths and replace its explicitly unmeasured host-load paragraph.
source = Path('scripts/summarize_cost_batch45.py').read_text(encoding='utf-8')
source = source.replace('batch45', 'batch51').replace('batch44', 'batch48')
old = "    report['host_load']={'trial_host_busy':'unmeasured','trial_host_available_ram':'unmeasured','pre_window_observation':'Parent observed about1.32GiB available RAM and active user applications; not a complete-window sample','harness_modified_during_run':False,'extra_runs_for_background':False}"
assert source.count(old) == 1
new = """    report['host_load']={
        'trials':[{side:verify_host(row[side]) for side in ('before','after')} for row in summary['runs']],
        'scope':'Pertrial whole-host CPU including benchmark and user background;0.25s RAM samples;sampled minimum not continuous minimum;Win32 thread CPU separate',
        'harness_modified_during_run':False,'extra_runs_for_background':False}
    report['host_sampler_sha']=sha('scripts/host_sampler_batch51.py')
    report['measurement_driver_sha']=sha('scripts/paired_benchmark_batch51.py')
    report['actual_baseline_scope']='R48 actual default archive54fc,not historical measured991e'
"""
source = source.replace(old, new)
exec(compile(source, 'summarize_cost_batch51_adapted', 'exec'))
