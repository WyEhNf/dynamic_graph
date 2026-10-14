"""Root actual originalC whole streams and finalized per-matrix metrics audit."""
import hashlib,json,math,struct
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair');D=R/'functional-evidence';PLAN=R/'functional-plan-resource-supplement'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def headers(p):
    out=[]
    with Path(p).open('rb') as f:
        count=struct.unpack('<I',f.read(4))[0]
        for i in range(count):n=struct.unpack('<I',f.read(4))[0];assert 3<=n<=10000;out.append(n);f.seek(n*n*8,1)
        assert f.tell()==Path(p).stat().st_size
    return out
def equal(a,b):
    size=0
    with Path(a).open('rb') as x,Path(b).open('rb') as y:
        while True:
            left=x.read(1048576);right=y.read(1048576);assert left==right;size+=len(left)
            if not left:return size
def main():
    plan=read(PLAN/'plan.json');report=read(D/'report.json')
    assert sha(D/'report.json')=='740b7116a1751b164b9d6b64d003ee6f02f24659b2d6f40441ad1b159ba8cef5'
    assert report['passed'] and not report['performance_executed'] and report['owner_PID']==136456
    assert report['plan_sha256']==sha(PLAN/'plan.json')
    for path,item in plan['source_files'].items():assert sha(PLAN/path)==item['sha256']
    assert report['compile']['command']==plan['compile_command'] and report['compile']['actual_exitcode']==0
    assert report['observer_EXE_sha256']==sha(D/'functional-observer.exe')
    assert len(report['records'])==54 and len(report['pairs'])==len(plan['cases'])==27
    assert len(report['resource_gate_observations'])==109 and all(g['passed'] and min(g['available_RAM_bytes'],g['free_G_bytes'])>=1073741824 for g in report['resource_gate_observations'])
    totalbytes=matrixcount=0;dynamic=Counter();engines=Counter();lastpcs=Counter();originalrefs=set()
    for case,pair,start in zip(plan['cases'],report['pairs'],range(0,54,2),strict=True):
        records=report['records'][start:start+2];assert pair['identity']==case['identity'] and pair['passed']
        for record,backend in zip(records,plan['backends'],strict=True):
            assert record['identity']==case['identity'] and record['backend']==backend and record['case']==case
            assert record['actual_exitcode']==0 and record['fresh_resources']['passed']
            for name,path in case['paths'].items():assert sha(path)==case['hashes'][name]==record['actual_reference_sha256'][name]
            originalrefs.add(case['hashes']['source.c']);assert headers(case['paths']['input.bin'])==headers(case['paths']['oracle.bin'])==case['input_matrix_headers']
            assert sha(record['raw_stdout'])==record['raw_stdout_sha256'] and sha(record['raw_stderr'])==record['raw_stderr_sha256']
            messages=[json.loads(line) for line in Path(record['raw_stdout']).read_text().splitlines()];assert messages[:-1]==record['matrices'] and messages[-1]==record['summary']
            summary=messages[-1];assert summary['step_limit_default']==1000000000 and summary['vm_budget_mode']=='fixed' and summary['step_limit_explicit'] is False
            assert len(messages)-1==summary['matrices']==case['matrices'] and summary['vm_steps']==sum(m['vm_steps'] for m in messages[:-1])
            if case['expected_vm_steps'] is not None:assert summary['vm_steps']==case['expected_vm_steps']
            for i,m in enumerate(messages[:-1]):
                assert m['n']==case['input_matrix_headers'][i] and m['index']==i and not m['error'];matrixcount+=1;engines[m['engine']]+=1
                assert m['vm_budget_work']==m['vm_budget_proof_ms']==0
                assert all(math.isfinite(m[k]) and m[k]>=0 for k in ['compute_ms_functional_only','vm_prepare_ms','vm_fusion_plan_ms'])
                assert m['vm_fusion_plan_ms']<=m['vm_prepare_ms']+1e-8<=m['compute_ms_functional_only']+2e-8
                if case['default_path_scope']=='native-control':
                    assert m['engine']!='vm' and not m['lastpc_applicable'] and m['vm_steps']==0 and m['vm_fusion_pairs_executed']==m['vm_fusion_pairs_discovered']==0
                else:
                    assert m['engine']=='vm' and m['backend']==backend and m['lastpc_applicable'] and m['vm_effective_step_limit']==1000000000
                    assert type(m['vm_last_pc']) is int and m['vm_last_pc']>=0;lastpcs[str(m['vm_last_pc'])]+=1
                    if backend=='decoded-threaded':assert m['vm_fusion_pairs_discovered']==m['vm_fusion_pairs_executed']==m['vm_fusion_plan_ms']==0
                    else:assert m['vm_fusion_status']=='entry-safe-pairs' and 0<=m['vm_fusion_pairs_executed']<=m['vm_steps']//2
                    dynamic[backend]+=m['vm_fusion_pairs_executed']
            output=Path(record['output']);assert output.drive.upper()=='G:' and not Path(str(output)+'.partial').exists()
            n=equal(output,case['paths']['oracle.bin']);assert n==case['reference_bytes'];totalbytes+=n
            assert headers(output)==case['input_matrix_headers'] and sha(output)==case['hashes']['oracle.bin']
        a,b=records
        for left,right in zip(a['matrices'],b['matrices'],strict=True):assert all(left[k]==right[k] for k in plan['compare_permatrix'])
    for row in [report['compile']]+report['records']:
        assert sha(row['raw_stdout'])==row['raw_stdout_sha256'] and sha(row['raw_stderr'])==row['raw_stderr_sha256']
        assert row['resource']['resource_samples']>=1 and row['resource']['host_available_ram_min_bytes']>0
    assert len(originalrefs)==19
    result=dict(passed=True,actual_terminal_exit_code=0,actual_tool_chunk='dcc174',actual_owner_session=45935,actual_owner_PID=136456,report_sha256=sha(D/'report.json'),observer_exe_sha256=report['observer_EXE_sha256'],whole_original_C_outputs=54,backend_pairs=27,true_C_sources=19,independent_full_bytes_compared=totalbytes,actual_matrix_results=matrixcount,engines=dict(engines),actual_fused_original_LOAD_pairs_executed=dynamic['decoded-threaded-load-pair'],actual_vm_last_pc_distribution=dict(lastpcs),fresh_resource_gates=109,per_matrix_original_steps_PC_errors_engine_equal=True,performance_measured=False,scope='Exact accepted87414 core/6591 header, frozen19 realC sources and27 streams, whole binary bytes and finalized actual steps/PC independently checked. Native default controls remain separate from forcedVM. Functional observer timing is not a performance baseline; arbitraryC and official85 compute score remain unproved.',authorized_next='Source-review fixed original19 samea95 CLI95 alternating compute pairs, resources/IO-exclusion/fullC negatives before one actual cost batch. No default promotion.')
    (ROOT/'outputs/stage2-root-load-pair-functional-actual.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
