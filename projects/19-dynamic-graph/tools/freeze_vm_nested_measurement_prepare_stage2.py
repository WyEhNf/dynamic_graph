"""Freeze already prepared cost/probe sources and their complete Python import closure."""
import ast, hashlib, json, shutil
from pathlib import Path

P = Path(__file__).resolve().parents[1]
S = P / 'artifacts/stage2-vm-nested-budget'
OUT = S / 'next-prepared'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''): h.update(part)
    return h.hexdigest()

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    assert not OUT.exists()
    cost = read(S / 'policy-cost/run-plan.json'); probe = read(S / 'analysis-only/run-plan.json')
    assert cost['records'] == 174 and cost['pairs'] == 87 and probe['observations'] == 25
    assert not (S / 'policy-cost/report.json').exists()
    assert not (S / 'analysis-only/compile-report.json').exists()
    assert not (S / 'analysis-only/probe.exe').exists() and not (S / 'analysis-only/report.json').exists()
    OUT.mkdir(); closure = {}; pending = [P / 'tools' / name for name in [
        'benchmark_vm_nested_policy_stage2.py', 'run_vm_nested_analysis_probe_stage2.py',
        'freeze_vm_nested_measurement_prepare_stage2.py']]
    while pending:
        source = pending.pop(); relative = source.relative_to(P).as_posix()
        if relative in closure: continue
        tree = ast.parse(source.read_text(encoding='utf-8'))
        destination = OUT / 'source' / relative; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        closure[relative] = {'origin': str(source), 'sha256': sha(source), 'bytes': source.stat().st_size}
        assert sha(destination) == closure[relative]['sha256']
        for node in ast.walk(tree):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 else
                       [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                if module:
                    local = P / 'tools' / (module.split('.')[0] + '.py')
                    if local.exists(): pending.append(local)
    for name in ['tools/vm_nested_analysis_probe_stage2.cpp', 'docs/stage2-vm-nested-measurement-prepare.md']:
        source = P / name; destination = OUT / 'source' / name; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        closure[name] = {'origin': str(source), 'sha256': sha(source), 'bytes': source.stat().st_size}
    plans = {}
    for name in ['policy-cost/run-plan.json', 'analysis-only/run-plan.json', 'next-static-design/plan.json']:
        source = S / name; destination = OUT / name; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination); plans[name] = {'origin': str(source), 'sha256': sha(source)}
    for relative, digest in cost['source_snapshot_sha256'].items(): assert sha(S / 'policy-cost' / relative) == digest
    for relative, digest in probe['frozen_files'].items(): assert sha(S / 'analysis-only' / relative) == digest
    for case in cost['cases']:
        for name, digest in case['hashes'].items(): assert sha(case['paths'][name]) == digest
    assert sha(cost['binary']['path']) == cost['binary']['sha256']
    assert sha(P / 'build/cholesky_runtime.exe') == cost['ordinary_sha256']
    assert sha(P / 'build-memory/cholesky_runtime.exe') == cost['memory_sha256']
    manifest = {'schema': 'optional-nested-VM-measurement-preparation-manifest-v1',
                'status': 'static preparation complete; source/resource review required before compiler, probe or cost execution',
                'source_files': closure, 'plans': plans, 'cost_case_count': 29, 'cost_records': 174,
                'cost_pairs': 87, 'VM_pairs': 69, 'native_pairs': 18, 'probe_observations': 25,
                'cost_EXE_sha256': cost['binary']['sha256'], 'probe_new_ABI': probe['ABI'],
                'all_case_files_and_frozen_source_hashes_checked': True,
                'compiler_C_VM_proof_cost_execution_count': 0, 'ordinary_or_default_changed': False,
                'ordinary_sha256': cost['ordinary_sha256'], 'memory_sha256': cost['memory_sha256'],
                'planned_output_bytes': cost['expected_output_bytes_total'],
                'cost_prepare_RAM_bytes': cost['prepare_available_RAM_bytes'], 'probe_prepare_RAM_bytes': probe['prepare_available_RAM_bytes'],
                'current_F_free_bytes': shutil.disk_usage(P).free,
                'Python_import_closure_note': 'evaluate_source imports frontend modules; these are frozen for provenance but no analyze/compiler/VM functions run in preparation/cost/probe. Only exact_compare is used.',
                'future_commands': [
                    ['.venv/Scripts/python.exe', 'tools/run_vm_nested_analysis_probe_stage2.py', '--compile'],
                    ['.venv/Scripts/python.exe', 'tools/run_vm_nested_analysis_probe_stage2.py', '--run'],
                    ['.venv/Scripts/python.exe', 'tools/benchmark_vm_nested_policy_stage2.py', '--run']],
                'no_maximum_matrix_or_C_execution_authorized_here': True}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'prepared': True, 'manifest_sha256': sha(OUT / 'manifest.json'),
                      'source_files': len(closure), 'cost_records': 174, 'probe_observations': 25,
                      'compiler_C_VM_proof_cost_executed': False}), flush=True)

if __name__ == '__main__': main()
