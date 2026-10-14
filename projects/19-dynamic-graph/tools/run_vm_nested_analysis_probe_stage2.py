"""Prepare an immutable matching-ABI, allocation-free analysis probe.

--compile and --run are separate future authorized phases, never implied by preparation.
"""
import argparse, hashlib, json, os, re, shutil, time
from pathlib import Path
from benchmark_vm_nested_policy_stage2 import available, copy_checked, read, sha, write
from windows_file_resource_probe_stage2 import monitored_run

P = Path(__file__).resolve().parents[1]
STAGE = P / 'artifacts/stage2-vm-nested-budget'
ROOT = STAGE / 'analysis-only'
DESIGN = STAGE / 'next-static-design/plan.json'
ACCEPT = STAGE / 'runtime-integration/acceptance'

def prepare():
    design = read(DESIGN); accepted = read(ACCEPT / 'manifest.json')
    assert accepted['passed'] and sha(ACCEPT / 'manifest.json') == design['accepted_manifest_sha256']
    assert not ROOT.exists(), 'immutable preparation already exists'
    ROOT.mkdir(); copy_checked(DESIGN, ROOT / 'design-plan.json')
    shutil.copytree(ACCEPT / 'source', ROOT / 'implementation-source')
    build = ACCEPT / 'builds/gnu-nested'
    core = build / 'libcholesky_core.a'
    core_sha = accepted['matching_four_new_ABI_builds']['gnu-nested']['artifacts']['libcholesky_core.a']['sha256']
    copy_checked(core, ROOT / 'libcholesky_core.a', core_sha)
    for name in ['CMakeCache.txt', 'CMakeFiles/cholesky_core.dir/flags.make',
                 'CMakeFiles/cholesky_core.dir/link.txt', 'CMakeFiles/cholesky_core.dir/build.make',
                 'CMakeFiles/cholesky_runtime.dir/flags.make', 'CMakeFiles/cholesky_runtime.dir/link.txt']:
        copy_checked(build / name, ROOT / 'build-provenance' / name)
    # The rsp is auxiliary command provenance; the accepted archive/source are the ABI authority.
    rsp = STAGE / 'runtime-integration/build-gnu-nested/CMakeFiles/cholesky_runtime.dir/linkLibs.rsp'
    copy_checked(rsp, ROOT / 'build-provenance/linkLibs.rsp')
    assert 'libcholesky_core.a -lpthread' in rsp.read_text()
    for source in [Path(__file__), P / 'tools/vm_nested_analysis_probe_stage2.cpp',
                   P / 'tools/benchmark_vm_nested_policy_stage2.py',
                   P / 'tools/windows_file_resource_probe_stage2.py', P / 'tools/evaluate_source.py']:
        copy_checked(source, ROOT / 'plan-source' / source.relative_to(P))
    cpp = ROOT / 'plan-source/tools/vm_nested_analysis_probe_stage2.cpp'
    include = ROOT / 'implementation-source/include'
    flags_text = (ROOT / 'build-provenance/CMakeFiles/cholesky_core.dir/flags.make').read_text()
    flags = re.search(r'^CXX_FLAGS = (.+)$', flags_text, re.MULTILINE)[1].split()
    definitions = re.search(r'^CXX_DEFINES = (.+)$', flags_text, re.MULTILINE)[1].split()
    assert '-fno-fast-math' in flags and '-ffp-contract=off' in flags and '-std=gnu++20' in flags
    assert '-DCHOL_NESTED_VM_BUDGET=1' in definitions
    command = ['E:/mingw64/bin/g++.exe', *flags, *definitions, '-I', str(include), str(cpp),
               str(ROOT / 'libcholesky_core.a'), '-lpthread', '-o', str(ROOT / 'probe.exe')]
    cases = []
    names = ['nested-rect-strides', 'nested-triangular', 'nested-gram-three',
             'unknown-data-step', 'unknown-parent-bound-write']
    for label in names:
        source = next(c for c in design['cost_scope']['cases'] if c.get('source_label') == label and c['family'] == 'dense')
        meta = ROOT / 'metadata' / (label + '.meta')
        copy_checked(source['paths']['program.meta'], meta, source['hashes']['program.meta'])
        for n in [3073, 6145, 8193, 9999, 10000]:
            prediction = next((p for p in design['predictions'].get(label, {}).get('points', []) if p['N'] == n), None)
            cases.append({'source': label, 'N': n, 'block': 32, 'metadata': str(meta),
                          'metadata_sha256': source['hashes']['program.meta'],
                          'source_C_path': source['paths']['source.c'], 'source_C_sha256': source['hashes']['source.c'],
                          'static_expected_state': 'proved' if prediction else 'unknown',
                          'static_predicted_bound': prediction['predicted_conservative_bound'] if prediction else None,
                          'predicted_actual_steps_not_executed': prediction['predicted_actual_steps_from_complete_instruction_layout'] if prediction else None,
                          'expectations_are_independent_test_gold_not_runtime_routing': True})
    snapshot = {x.relative_to(ROOT).as_posix(): sha(x) for x in sorted(ROOT.rglob('*')) if x.is_file()}
    plan = {'schema': 'optional-nested-VM-analysis-only-plan-v1',
            'status': 'prepared; no compile or proof execution authorized by this preparation',
            'design_sha256': sha(DESIGN), 'acceptance_manifest_sha256': sha(ACCEPT / 'manifest.json'),
            'frozen_files': snapshot, 'ABI': {'header_sha256': sha(include / 'cholesky/runtime.hpp'),
                'core_sha256': core_sha, 'header_and_core_same_accepted_new_ABI_build': True,
                'old_572_core_forbidden': True},
            'compile_command': command, 'compiler_version_provenance': 'matching accepted CMakeCache/flags, no compiler invocation during prepare',
            'cases': cases, 'observations': 25, 'positive_bound_observations': 15, 'unknown_safety_observations': 10,
            'scope': 'three trueC nested PROGRAMs plus two unchanged trueC unknown controls; no Matrix or VM execution; native bypass is measured only in cost controls',
            'work_limit': 250000, 'first_then_nested_only_if_unknown_and_remaining_positive': True,
            'reason_work_limit_does_not_imply_zero_remaining': True, 'effective_cap': 'proved max(1e9,bound), unknown 1e9',
            'timers': ['metadata_read_ms outside proof', 'first_ms', 'nested_ms', 'proof_ms includes stage selection and metrics', 'dispatch_and_metric_ms=proof-first-nested', 'process_wall_ms', 'separate SHA check'],
            'shared_work_counters': ['first_work', 'remaining_after_first', 'nested_work', 'shared_work', 'work_limit'],
            'matrix_allocations': 0, 'VM_executions': 0, 'originalC_executions': 0, 'native_executions': 0,
            'minimum_fresh_RAM_bytes': 268435456, 'minimum_free_F_bytes': 268435456,
            'compiler_temp': str(STAGE / 'compiler-temp'), 'file_stdio_only': True,
            'failure_preserve_no_retry': True, 'ordinary_runtime_changed': False,
            'ordinary_sha256': design['ordinary_runtime_sha256'], 'memory_sha256': design['memory_runtime_sha256'],
            'prepare_available_RAM_bytes': available(), 'prepare_free_F_bytes': shutil.disk_usage(ROOT).free}
    write(ROOT / 'run-plan.json', plan)
    print(json.dumps({'prepared': True, 'plan_sha256': sha(ROOT / 'run-plan.json'),
                      'observations': 25, 'ABI': plan['ABI'], 'compiler_or_analysis_executed': False}), flush=True)

def verify(plan):
    assert sha(DESIGN) == plan['design_sha256'] and sha(ACCEPT / 'manifest.json') == plan['acceptance_manifest_sha256']
    for relative, digest in plan['frozen_files'].items(): assert sha(ROOT / relative) == digest
    for name in ['run_vm_nested_analysis_probe_stage2.py', 'benchmark_vm_nested_policy_stage2.py',
                 'windows_file_resource_probe_stage2.py', 'evaluate_source.py', 'vm_nested_analysis_probe_stage2.cpp']:
        assert sha(P / 'tools' / name) == plan['frozen_files']['plan-source/tools/' + name]
    assert sha(P / 'build/cholesky_runtime.exe') == plan['ordinary_sha256']
    assert sha(P / 'build-memory/cholesky_runtime.exe') == plan['memory_sha256']

def resource_gate(plan):
    gate = {'available_RAM_bytes': available(), 'free_F_bytes': shutil.disk_usage(ROOT).free,
            'minimum_RAM_bytes': plan['minimum_fresh_RAM_bytes'], 'minimum_F_bytes': plan['minimum_free_F_bytes']}
    gate['passed'] = gate['available_RAM_bytes'] >= gate['minimum_RAM_bytes'] and gate['free_F_bytes'] >= gate['minimum_F_bytes']
    return gate

def compile_probe():
    plan = read(ROOT / 'run-plan.json'); verify(plan)
    report_path = ROOT / 'compile-report.json'
    assert not report_path.exists() and not (ROOT / 'probe.exe').exists(), 'single compiler attempt; do not restart'
    gate = resource_gate(plan)
    report = {'schema': 'optional-nested-VM-analysis-probe-compile-v1', 'passed': False,
              'plan_sha256': sha(ROOT / 'run-plan.json'), 'command': plan['compile_command'],
              'resource_gate': gate, 'environment': {k: os.environ[k] for k in ['TEMP', 'TMP', 'TMPDIR']}}
    write(report_path, report)
    if not gate['passed']: raise SystemExit(75)
    proc, resources = monitored_run(plan['compile_command'], ROOT / 'compile.stdout', ROOT / 'compile.stderr', check=False)
    report.update(actual_exit_code=proc.returncode, resources=resources,
                  raw_stdout=str(ROOT / 'compile.stdout'), raw_stderr=str(ROOT / 'compile.stderr'),
                  raw_stdout_sha256=sha(ROOT / 'compile.stdout'), raw_stderr_sha256=sha(ROOT / 'compile.stderr'))
    if proc.returncode == 0: report.update(passed=True, EXE_sha256=sha(ROOT / 'probe.exe'))
    write(report_path, report)
    print(json.dumps(report), flush=True)
    if proc.returncode: raise SystemExit(proc.returncode)

def run():
    plan = read(ROOT / 'run-plan.json'); verify(plan); compiled = read(ROOT / 'compile-report.json')
    assert compiled['passed'] and sha(ROOT / 'probe.exe') == compiled['EXE_sha256']
    report_path = ROOT / 'report.json'; assert not report_path.exists(), 'never restart an observed batch'
    report = {'schema': 'optional-nested-VM-analysis-only-report-v1', 'passed': False, 'status': 'running',
              'plan_sha256': sha(ROOT / 'run-plan.json'), 'probe_EXE_sha256': compiled['EXE_sha256'],
              'records': [], 'resource_gates': [], 'matrix_or_C_or_VM_execution': False}
    write(report_path, report)
    try:
        for case in plan['cases']:
            checked = time.perf_counter()
            assert sha(case['metadata']) == case['metadata_sha256'] and sha(case['source_C_path']) == case['source_C_sha256']
            assert sha(ROOT / 'probe.exe') == compiled['EXE_sha256']
            sha_ms = (time.perf_counter() - checked) * 1000
            gate = resource_gate(plan); report['resource_gates'].append({**gate, 'source': case['source'], 'N': case['N']})
            write(report_path, report)
            if not gate['passed']:
                report.update(status='resource-gate-blocked', pending=case); write(report_path, report); raise SystemExit(75)
            stem = case['source'] + '-' + str(case['N']); stdout = ROOT / (stem + '.stdout'); stderr = ROOT / (stem + '.stderr')
            command = [str(ROOT / 'probe.exe'), case['metadata'], str(case['N']), str(case['block'])]
            start = time.perf_counter(); proc, resource = monitored_run(command, stdout, stderr, check=False)
            wall_ms = (time.perf_counter() - start) * 1000
            report['last_actual_process'] = {'case': case, 'exit_code': proc.returncode, 'raw_stdout': str(stdout),
                                             'raw_stderr': str(stderr), 'resources': resource}; write(report_path, report)
            assert proc.returncode == 0, proc.stderr
            metric = json.loads(proc.stdout)
            assert metric['N'] == case['N'] and metric['block'] == case['block']
            assert metric['matrix_allocations'] == metric['VM_executions'] == metric['native_executions'] == 0
            assert 0 <= metric['shared_work'] <= 250000
            assert metric['shared_work'] == metric['first_work'] + metric['nested_work']
            assert metric['remaining_after_first'] == 250000 - metric['first_work']
            assert metric['nested_work'] <= metric['remaining_after_first']
            if metric['first_proved']: assert not metric['nested_called'] and metric['selected_stage'] == 'first'
            if not metric['remaining_after_first']: assert not metric['nested_called']
            assert metric['effective_cap'] == (max(1000000000, metric['bound']) if metric['proved'] else 1000000000)
            expected = (metric['proved'] and metric['bound'] == case['static_predicted_bound']) if case['static_expected_state'] == 'proved' else not metric['proved']
            row = {**case, **metric, **resource, 'static_expectation_matched': expected,
                   'command': command, 'actual_exit_code': proc.returncode, 'process_wall_ms': wall_ms,
                   'sha_validation_ms': sha_ms, 'raw_stdout': str(stdout), 'raw_stderr': str(stderr),
                   'raw_stdout_sha256': sha(stdout), 'raw_stderr_sha256': sha(stderr)}
            report['records'].append(row); write(report_path, report)
            print(json.dumps({'source': case['source'], 'N': case['N'], 'proved': metric['proved'],
                              'bound': metric['bound'], 'shared_work': metric['shared_work'], 'expectation_matched': expected}), flush=True)
        assert len(report['records']) == 25
        report.update(status='complete', passed=all(r['static_expectation_matched'] for r in report['records']))
        write(report_path, report)
        print(json.dumps({'passed': report['passed'], 'observations': 25, 'report_sha256': sha(report_path)}), flush=True)
        if not report['passed']: raise SystemExit(1)
    except BaseException as error:
        if report['status'] not in ['resource-gate-blocked', 'complete']: report.update(status='first-failure', failure=str(error))
        write(report_path, report); raise

def main():
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    for option in ['prepare', 'compile', 'run']: group.add_argument('--' + option, action='store_true')
    args = parser.parse_args(); temp = STAGE / 'compiler-temp'; temp.mkdir(exist_ok=True)
    os.environ.update({key: str(temp) for key in ['TEMP', 'TMP', 'TMPDIR']})
    if args.prepare: prepare()
    elif args.compile: compile_probe()
    else: run()

if __name__ == '__main__': main()
