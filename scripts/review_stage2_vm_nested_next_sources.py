"""Verify frozen same-runtime cost runner and allocation-free high-N proof probe."""
import ast,hashlib,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/19-dynamic-graph';D=P/'artifacts/stage2-vm-nested-budget'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    cost=read(D/'policy-cost/run-plan.json');probe=read(D/'analysis-only/run-plan.json')
    assert sha(D/'policy-cost/run-plan.json')=='38c54b9ac38c8e26b11d8ce12953b58b512b994291d2a674f460bbd05eca813b'
    assert sha(D/'analysis-only/run-plan.json')=='d4f37ab48eecd0ba1e60a92a744e72617d4e1490ed36661a8b4c2b5a43b6a80f'
    design=read(D/'next-static-design/plan.json')
    for plan,folder,key in [(cost,'policy-cost','source_snapshot_sha256'),(probe,'analysis-only','frozen_files')]:
        assert plan['design_sha256']==sha(D/'next-static-design/plan.json')
        assert plan['acceptance_manifest_sha256']==sha(D/'runtime-integration/acceptance/manifest.json')
        for name,digest in plan[key].items(): assert sha(D/folder/name)==digest
        for name,digest in plan[key].items():
            if name.startswith('plan-source/tools/'):
                assert sha(P/name.removeprefix('plan-source/'))==digest
                if name.endswith('.py'):ast.parse((D/folder/name).read_text(encoding='utf-8'))
    assert sha(cost['binary']['path'])==cost['binary']['sha256']==design['same_binary']['sha256']
    assert (cost['records'],cost['pairs'],cost['VM_records'],cost['native_records'])==(174,87,138,36)
    assert len(cost['cases'])==29
    for row in cost['cases']:
        for name,digest in row['hashes'].items():assert sha(row['paths'][name])==digest
    assert sum(row['reference_bytes'] for row in cost['cases'])*6==cost['expected_output_bytes_total']==495920904
    assert probe['ABI']['header_sha256']=='1955d364a3b097c05e3972ec29fb86c1e9fbed5622294e1b40bcba7894f3bf9d'
    assert probe['ABI']['core_sha256']==sha(D/'analysis-only/libcholesky_core.a')=='4598bcb8fa66b7f78891530ea6dd857129bfc53af4c88e5d98a7fca89941a079'
    assert all(flag in probe['compile_command'] for flag in ['-fno-fast-math','-ffp-contract=off','-std=gnu++20','-DCHOL_NESTED_VM_BUDGET=1'])
    assert len(probe['cases'])==25 and {c['N']for c in probe['cases']}=={3073,6145,8193,9999,10000}
    for c in probe['cases']:assert sha(c['metadata'])==c['metadata_sha256'] and sha(c['source_C_path'])==c['source_C_sha256']
    text=(P/'tools/vm_nested_analysis_probe_stage2.cpp').read_text()
    for forbidden in ['chol::Matrix','chol::read_matrix','chol::execute','execute_prepared','execute_threaded']:assert forbidden not in text
    assert 'metadata.program.size()' in text and 'work_limit-first.work' in text
    result=dict(passed=True,reviewed_unix=time.time(),cost_plan_sha256=sha(D/'policy-cost/run-plan.json'),probe_plan_sha256=sha(D/'analysis-only/run-plan.json'),cost_cases=29,planned_records=174,planned_pairs=87,planned_output_bytes=495920904,probe_observations=25,
        authorization='Compile the frozen matching-ABI analysis-only probe once and execute25 observations under fresh256MiB RAM/disk gates. Then run exactly frozen174 samebinary fixed/proved cost records once with wholeCbyte comparisons and resource gates after root/otheragent CPU audits finish; keep all negatives and failures. No large matrix/realC run/default promotion.',
        scope='All frozen source/helper/case hashes and matching accepted ABI/strictFP compiler provenance verified. Probe cannot allocate or execute matrices; highN bound evaluation does not demonstrate highN runtime output. Cost runner scope is only old29 unamplified cases; no speedup claim before actual results.')
    (ROOT/'outputs/stage2-root-vm-nested-next-sources.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
