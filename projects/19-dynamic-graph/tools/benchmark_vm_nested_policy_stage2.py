"""Static preparation and separately authorized same-844 fixed/proved cost batch.

Preparation copies accepted artifacts; it does not execute a compiler, C or VM.
"""
import argparse, ctypes, hashlib, json, os, shutil, statistics, struct, time
from pathlib import Path
from evaluate_source import exact_compare
from windows_file_resource_probe_stage2 import HostMemory, monitored_run

P = Path(__file__).resolve().parents[1]
STAGE = P / 'artifacts/stage2-vm-nested-budget'
ROOT = STAGE / 'policy-cost'
DESIGN = STAGE / 'next-static-design/plan.json'
ACCEPT = STAGE / 'runtime-integration/acceptance'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')

def available():
    value = HostMemory(); value.dwLength = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise ctypes.WinError()
    return value.ullAvailPhys

def headers(path):
    sizes = []
    with Path(path).open('rb') as stream:
        count = struct.unpack('<I', stream.read(4))[0]
        for _ in range(count):
            n = struct.unpack('<I', stream.read(4))[0]
            assert 3 <= n <= 10000
            sizes.append(n); stream.seek(8 * n * n, 1)
        assert stream.tell() == Path(path).stat().st_size and stream.read() == b''
    return sizes

def copy_checked(source, dest, expected=None):
    digest = sha(source)
    if expected is not None:
        assert digest == expected, str(source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    assert sha(dest) == digest
    return digest

def prepare():
    design = read(DESIGN); accept = read(ACCEPT / 'manifest.json')
    assert accept['passed'] and sha(ACCEPT / 'manifest.json') == design['accepted_manifest_sha256']
    assert not ROOT.exists(), 'immutable preparation directory already exists'
    ROOT.mkdir()
    copy_checked(DESIGN, ROOT / 'design-plan.json')
    exe = ACCEPT / 'builds/gnu-nested/cholesky_runtime.exe'
    copy_checked(exe, ROOT / 'runtime.exe', design['same_binary']['sha256'])
    shutil.copytree(ACCEPT / 'source', ROOT / 'implementation-source')
    build = ACCEPT / 'builds/gnu-nested'
    for name in ['CMakeCache.txt', 'CMakeFiles/cholesky_core.dir/flags.make',
                 'CMakeFiles/cholesky_core.dir/link.txt', 'CMakeFiles/cholesky_core.dir/build.make',
                 'CMakeFiles/cholesky_runtime.dir/flags.make', 'CMakeFiles/cholesky_runtime.dir/link.txt']:
        copy_checked(build / name, ROOT / 'implementation-build' / name)
    helpers = [Path(__file__), P / 'tools/windows_file_resource_probe_stage2.py', P / 'tools/evaluate_source.py']
    for source in helpers:
        copy_checked(source, ROOT / 'plan-source' / source.relative_to(P))
    cases = []
    for original in design['cost_scope']['cases']:
        case = dict(original); folder = ROOT / case['source']; folder.mkdir()
        for name, source in case['paths'].items():
            copy_checked(source, folder / name, case['hashes'][name])
        assert headers(folder / 'input.bin') == headers(folder / 'oracle.bin') == case['input_matrix_headers']
        assert (folder / 'oracle.bin').stat().st_size == case['reference_bytes']
        case['paths'] = {name: str(folder / name) for name in case['hashes']}
        # Previous first-stage expectations are lineage, never assertions of final nested state.
        case['prior_expected_proof_status_is_not_final_nested_assertion'] = True
        cases.append(case)
    snapshot = {x.relative_to(ROOT).as_posix(): sha(x) for folder in
                ['implementation-source', 'implementation-build', 'plan-source']
                for x in sorted((ROOT / folder).rglob('*')) if x.is_file()}
    assert len(cases) == 29 and sum(x['kind'] == 'vm' for x in cases) == 23
    plan = {
        'schema': 'optional-nested-VM-policy-cost-run-plan-v1',
        'status': 'prepared only; cost execution requires root window authorization',
        'design_sha256': sha(DESIGN), 'acceptance_manifest_sha256': sha(ACCEPT / 'manifest.json'),
        'binary': {'path': str(ROOT / 'runtime.exe'), 'sha256': sha(ROOT / 'runtime.exe')},
        'source_snapshot_sha256': snapshot, 'cases': cases,
        'rounds': 3, 'records': 174, 'pairs': 87, 'VM_records': 138, 'VM_pairs': 69,
        'native_records': 36, 'native_pairs': 18,
        'pair_order': 'case-major; round0 fixed/proved, round1 proved/fixed, round2 fixed/proved',
        'threads': 4, 'scheduler': 'parallel', 'sole_variation': '--vm-budget fixed versus proved',
        'explicit_step_limit': None, 'backend_override': None,
        'proof_first_nested_and_dispatch_inside_compute': True,
        'no_new_C_or_reference_execution': True, 'source_specific_runtime_selection': False,
        'minimum_launch_RAM_bytes': 268435456, 'minimum_disk_reserve_bytes': 536870912,
        'expected_output_bytes_total': sum(x['reference_bytes'] for x in cases) * 6,
        'first_failure_preserved_no_restart': True, 'all_unknown_and_negative_retained': True,
        'user_apps_untouched_host_not_claimed_idle': True,
        'ordinary_sha256': design['ordinary_runtime_sha256'], 'memory_sha256': design['memory_runtime_sha256'],
        'prepare_available_RAM_bytes': available(), 'prepare_free_F_bytes': shutil.disk_usage(ROOT).free,
        'resource_probe_scope': 'actual runtime process PeakWS/commit and sampled whole-host CPU/RAM; IO/startup included in process wall',
        'raw_capture': 'file stdout/stderr, never an undrained PIPE',
        'compiler_temp': str(STAGE / 'compiler-temp'),
        'primary_refs': ['https://llvm.org/docs/LoopTerminology.html', 'https://llvm.org/doxygen/classllvm_1_1ScalarEvolution.html']}
    write(ROOT / 'run-plan.json', plan)
    print(json.dumps({'prepared': True, 'plan_sha256': sha(ROOT / 'run-plan.json'), 'records': 174,
                      'pairs': 87, 'output_bytes': plan['expected_output_bytes_total'],
                      'RAM': plan['prepare_available_RAM_bytes'], 'F_free': plan['prepare_free_F_bytes'],
                      'compiler_C_VM_or_cost_executed': False}), flush=True)

def verify_metrics(case, mode, m):
    assert m['matrices'] == case['matrices'] and m['vm_budget_mode'] == mode
    for key in ['vm_budget_proof_ms', 'vm_prepare_ms', 'vm_budget_first_ms', 'vm_budget_nested_ms']:
        assert 0 <= m[key] <= m['compute_ms']
    # Output JSON prints finite decimal times; don't demand exact floating sum equality.
    assert m['vm_budget_first_work'] + m['vm_budget_nested_work'] == m['vm_budget_work']
    assert m['vm_budget_work'] <= 250000 * case['matrices']
    if case['kind'] == 'vm':
        assert m['selected_engine'] == 'vm' and m['vm_backend'] == 'decoded-threaded'
        assert m['vm_steps'] == case['expected_vm_steps']
        assert m['vm_effective_step_limit_max'] == max(1000000000, m['vm_budget_bound_peak'])
        if mode == 'fixed':
            for key in ['vm_budget_proof_ms', 'vm_budget_first_ms', 'vm_budget_nested_ms',
                        'vm_budget_work', 'vm_budget_first_work', 'vm_budget_nested_work',
                        'vm_budget_proved_matrices', 'vm_budget_unknown_matrices',
                        'vm_budget_first_proved_matrices', 'vm_budget_first_unknown_matrices',
                        'vm_budget_nested_attempted_matrices']:
                assert m[key] == 0
        else:
            assert m['vm_budget_proved_matrices'] + m['vm_budget_unknown_matrices'] == case['matrices']
            assert m['vm_budget_first_proved_matrices'] + m['vm_budget_first_unknown_matrices'] == case['matrices']
            assert m['vm_budget_nested_proved_matrices'] + m['vm_budget_nested_unknown_matrices'] == m['vm_budget_nested_attempted_matrices']
            assert m['vm_budget_nested_attempted_matrices'] + m['vm_budget_nested_work_exhausted_skips'] == m['vm_budget_first_unknown_matrices']
            assert m['vm_budget_proved_matrices'] == m['vm_budget_first_proved_matrices'] + m['vm_budget_nested_proved_matrices']
        assert m['vm_budget_not_run_matrices'] == 0
    else:
        assert m['selected_engine'] in ['stage', 'tiled', 'diagonal'] and m['vm_backend'] == ''
        for key in ['vm_steps', 'vm_budget_proof_ms', 'vm_budget_work', 'vm_budget_bound_peak',
                    'vm_budget_first_ms', 'vm_budget_nested_ms', 'vm_budget_first_work', 'vm_budget_nested_work',
                    'vm_budget_first_proved_matrices', 'vm_budget_first_unknown_matrices',
                    'vm_budget_nested_attempted_matrices', 'vm_budget_proved_matrices',
                    'vm_budget_unknown_matrices', 'vm_effective_step_limit_max']:
            assert m[key] == 0
        assert m['vm_budget_not_run_matrices'] == case['matrices']
        if case.get('lineage', {}).get('expected_engine') == 'diagonal': assert m['selected_engine'] == 'diagonal'
        if case['engine_requested'] == 'tiled': assert m['selected_engine'] == 'tiled'

def run():
    plan = read(ROOT / 'run-plan.json')
    assert not (ROOT / 'report.json').exists(), 'never restart or overwrite a batch'
    assert sha(DESIGN) == plan['design_sha256'] and sha(ACCEPT / 'manifest.json') == plan['acceptance_manifest_sha256']
    for relative, digest in plan['source_snapshot_sha256'].items(): assert sha(ROOT / relative) == digest
    for name in ['benchmark_vm_nested_policy_stage2.py', 'windows_file_resource_probe_stage2.py', 'evaluate_source.py']:
        assert sha(P / 'tools' / name) == plan['source_snapshot_sha256']['plan-source/tools/' + name]
    assert sha(P / 'build/cholesky_runtime.exe') == plan['ordinary_sha256']
    assert sha(P / 'build-memory/cholesky_runtime.exe') == plan['memory_sha256']
    report = {'schema': 'optional-nested-VM-policy-cost-report-v1', 'passed': False, 'status': 'running',
              'plan_sha256': sha(ROOT / 'run-plan.json'), 'records': [], 'resource_gates': [],
              'ordinary_default_changed': False, 'new_C_or_reference_executions': 0}
    began = time.perf_counter()
    def save():
        report['elapsed_seconds'] = time.perf_counter() - began; write(ROOT / 'report.json', report)
    save()
    try:
        for case in plan['cases']:
            folder = ROOT / case['source']
            for round in range(plan['rounds']):
                for mode in (['fixed', 'proved'] if round % 2 == 0 else ['proved', 'fixed']):
                    context = {'source': case['source'], 'round': round, 'mode': mode}
                    began_check = time.perf_counter()
                    assert sha(plan['binary']['path']) == plan['binary']['sha256']
                    for name, digest in case['hashes'].items(): assert sha(folder / name) == digest
                    assert headers(folder / 'input.bin') == headers(folder / 'oracle.bin') == case['input_matrix_headers']
                    sha_ms = (time.perf_counter() - began_check) * 1000
                    ram = available(); free = shutil.disk_usage(ROOT).free
                    remaining = plan['expected_output_bytes_total'] - sum(r['bytes'] for r in report['records']) + plan['minimum_disk_reserve_bytes']
                    gate = {**context, 'available_RAM_bytes': ram, 'free_F_bytes': free,
                            'minimum_remaining_disk_bytes': remaining,
                            'passed': ram >= plan['minimum_launch_RAM_bytes'] and free >= remaining}
                    report['resource_gates'].append(gate); save()
                    if not gate['passed']:
                        report.update(status='resource-gate-blocked', pending=context); save(); raise SystemExit(75)
                    output = folder / f'round-{round}-{mode}.bin'; assert not output.exists()
                    stdout = folder / f'round-{round}-{mode}.stdout'; stderr = folder / f'round-{round}-{mode}.stderr'
                    command = [plan['binary']['path'], '--metadata', str(folder / 'program.meta'), '--input',
                               str(folder / 'input.bin'), '--output', str(output), '--engine', case['engine_requested'],
                               '--threads', str(plan['threads']), '--scheduler', plan['scheduler'],
                               '--block-size', str(case['block']), '--vm-budget', mode]
                    started = time.perf_counter()
                    proc, resource = monitored_run(command, stdout, stderr, check=False)
                    wall_ms = (time.perf_counter() - started) * 1000
                    report['last_actual_process'] = {**context, 'command': command, 'exit_code': proc.returncode,
                        'raw_stdout': str(stdout), 'raw_stderr': str(stderr), 'resource': resource}; save()
                    assert proc.returncode == 0, proc.stderr
                    metric = json.loads(proc.stdout); verify_metrics(case, mode, metric)
                    started = time.perf_counter(); match = exact_compare(folder / 'oracle.bin', output)
                    comparison_ms = (time.perf_counter() - started) * 1000
                    assert match['bytes'] == case['reference_bytes']
                    row = {**context, 'kind': case['kind'], 'scope': case['scope'], 'command': command,
                           'actual_exit_code': proc.returncode, 'exe_sha256': plan['binary']['sha256'],
                           'case_hashes': case['hashes'], 'metadata': str(folder / 'program.meta'),
                           'input': str(folder / 'input.bin'), 'reference': str(folder / 'oracle.bin'),
                           'output': str(output), 'raw_stdout': str(stdout), 'raw_stderr': str(stderr),
                           'raw_stdout_sha256': sha(stdout), 'raw_stderr_sha256': sha(stderr),
                           'sha_validation_ms': sha_ms, 'whole_file_comparison_ms': comparison_ms,
                           'process_wall_ms': wall_ms, 'available_RAM_before_bytes': ram, **metric, **resource, **match}
                    report['records'].append(row); save()
                    print(json.dumps({**context, 'compute_ms': metric['compute_ms'], 'first_ms': metric['vm_budget_first_ms'],
                                      'nested_ms': metric['vm_budget_nested_ms'], 'proved': metric['vm_budget_proved_matrices'],
                                      'unknown': metric['vm_budget_unknown_matrices'], 'byte_identical': True}), flush=True)
        pairs = []; summaries = []
        for case in plan['cases']:
            rows = [r for r in report['records'] if r['source'] == case['source']]; ratios = []; wall_ratios = []
            for round in range(plan['rounds']):
                fixed = next(r for r in rows if r['round'] == round and r['mode'] == 'fixed')
                proved = next(r for r in rows if r['round'] == round and r['mode'] == 'proved')
                ratio = proved['compute_ms'] / fixed['compute_ms']; wall = proved['process_wall_ms'] / fixed['process_wall_ms']
                ratios.append(ratio); wall_ratios.append(wall)
                pairs.append({'source': case['source'], 'kind': case['kind'], 'round': round,
                              'compute_ratio_proved_over_fixed': ratio, 'compute_delta_ms': proved['compute_ms'] - fixed['compute_ms'],
                              'wall_ratio_proved_over_fixed': wall, 'outcome': 'win' if ratio < 1 else 'negative' if ratio > 1 else 'tie'})
            summaries.append({'source': case['source'], 'kind': case['kind'], 'paired_compute_ratios': ratios,
                              'paired_wall_ratios': wall_ratios, 'median_paired_compute_ratio': statistics.median(ratios),
                              'median_paired_wall_ratio': statistics.median(wall_ratios),
                              'median_first_ms': statistics.median(r['vm_budget_first_ms'] for r in rows if r['mode'] == 'proved'),
                              'median_nested_ms': statistics.median(r['vm_budget_nested_ms'] for r in rows if r['mode'] == 'proved')})
        assert len(report['records']) == 174 and len(pairs) == 87
        report.update(passed=True, status='complete', pairs=pairs, summary=summaries,
                      negative_pairs=[x for x in pairs if x['outcome'] == 'negative'])
        save(); print(json.dumps({'passed': True, 'records': 174, 'pairs': 87, 'report_sha256': sha(ROOT / 'report.json')}), flush=True)
    except BaseException as error:
        if report['status'] != 'resource-gate-blocked': report.update(status='first-failure', failure=str(error))
        save(); raise

def main():
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true'); group.add_argument('--run', action='store_true')
    args = parser.parse_args(); temp = STAGE / 'compiler-temp'; temp.mkdir(exist_ok=True)
    os.environ.update({key: str(temp) for key in ['TEMP', 'TMP', 'TMPDIR']})
    if args.prepare: prepare()
    else: run()

if __name__ == '__main__': main()
