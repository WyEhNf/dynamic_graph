"""Root preserves failed runner, verifies actual successful first CLI output."""
import hashlib,json
from pathlib import Path
from review_stage2_load_pair_functional_actual import sha,equal,headers
ROOT=Path(__file__).resolve().parents[1];R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair');D=R/'performance-evidence'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    report=read(D/'report.json');plan=read(R/'performance-plan/plan.json')
    assert sha(D/'report.json')=='070392af398496ac4884a7889bf0b65017c1d4231a6387dc986a30d8e7b06804'
    assert not report['passed'] and len(report['records'])==1 and report['first_failure']['type']=='AssertionError'
    r=report['records'][0];c=plan['cases'][0];assert r['identity']==c['identity']=='changed-arithmetic' and r['round']==0 and r['backend']=='decoded-threaded'
    assert r['actual_exitcode']==0 and r['actual_exe_sha256']==plan['runtime']['sha256'];assert all(g['passed'] for g in report['resource_gate_observations'])
    metric=json.loads(Path(r['raw_stdout']).read_text());assert metric==r['metric'] and metric['vm_steps']==c['expected_vm_steps']==40026430
    for key in ['vm_budget_work','vm_budget_proof_ms','vm_budget_proved_matrices','vm_budget_unknown_matrices','vm_budget_not_run_matrices']:assert metric[key]==0
    assert metric['vm_budget_mode']=='fixed' and metric['vm_effective_step_limit_max']==1000000000
    for name,path in c['paths'].items():assert sha(path)==r['actual_reference_sha256'][name]==c['hashes'][name]
    assert equal(r['output'],c['paths']['oracle.bin'])==c['reference_bytes']==379700
    assert sha(r['output'])==c['hashes']['oracle.bin'] and headers(r['output'])==c['input_matrix_headers']
    for stream in ['stdout','stderr']:assert sha(r['raw_'+stream])==r['raw_'+stream+'_sha256']
    runtime=(R/'workspace/src/runtime.cpp').read_text();main=(R/'workspace/src/main.cpp').read_text()
    assert 'vm_budget_proof_status="fixed"' in runtime and 'vm_budget_not_run_matrices+=metrics.vm_budget_proof_status=="not-run"' in main
    result=dict(passed=True,first_runner_terminal_exit_code=1,first_tool_chunk='9e2aaf',actual_first_CLI_exit_code=0,first_originalC_bytes_independently_compared=379700,first_actual_compute_ms=metric['compute_ms'],failed_report_sha256=sha(D/'report.json'),cause='Runner asserted not-run count equalsmatrices for fixed genericVM; runtime sets fixed so count0; native bypass staysnot-run.',next='Source-only corrected assertion and missing189 continuation; preserve original raw/trace. Pair0 must be marked interrupted, separately from94 continuous comparisons. No favorable-only source selection.')
    (ROOT/'outputs/stage2-root-load-pair-first-cost-failure.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
