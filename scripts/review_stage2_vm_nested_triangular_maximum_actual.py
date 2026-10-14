"""Root independent full-file comparison and raw observation audit."""
import hashlib,json,struct,time
from pathlib import Path
from review_stage2_vm_nested_next_sources import ROOT,D,read,sha
def main():
    folder=D/'triangular-maximum'; report=read(folder/'report.json'); plan=read(folder/'run-plan.json')
    assert sha(folder/'report.json')=='0d1d33ccda6fd618fbacdb271201750653d689399ff48e35c7daa5a54b55eb88'
    assert report['passed'] and report['status']=='complete' and report['plan_sha256']==sha(folder/'run-plan.json')
    assert report['original_C_executions']==1 and report['VM_executions']==2
    assert not report['ordinary_changed'] and not report['performance_claim'] and not report['explicit_limit_used']
    runs=report['runs']; assert [r['stage'] for r in runs]==['original-C','fixed-default-rejection','GNUauto-proved']
    assert [r['actual_exit_code'] for r in runs]==[0,1,0]
    for row in runs:
        for suffix in ('stdout','stderr'): assert sha(row['raw_'+suffix])==row['raw_'+suffix+'_sha256']
        assert not Path(row['output']+'.partial').exists()
        assert row['available_RAM_before_bytes']>=2684354560
    ref,fixed,proved=runs
    assert Path(ref['raw_stdout']).read_bytes()==Path(ref['raw_stderr']).read_bytes()==b''
    assert Path(fixed['raw_stdout']).read_bytes()==b'' and Path(fixed['raw_stderr']).read_text()=='error: VM instruction limit exceeded\n'
    assert not Path(fixed['output']).exists()
    raw=read(proved['raw_stdout']); assert Path(proved['raw_stderr']).read_bytes()==b''
    assert all(proved[key]==value for key,value in raw.items())
    assert raw['vm_steps']==14*10000**2+3*10000+9==1400030009
    assert raw['vm_budget_bound_peak']==raw['vm_effective_step_limit_max']==28*10000**2-11*10000+9==2799890009
    assert raw['vm_budget_work']==24161 and raw['vm_budget_first_unknown_matrices']==1
    assert raw['vm_budget_nested_proved_matrices']==1 and raw['vm_budget_selected_stage_last']=='nested'
    assert raw['selected_engine']=='vm' and raw['vm_backend']=='decoded-threaded'
    assert '--vm-step-limit' not in proved['command'] and proved['command'][-2:]==['--vm-budget','proved']
    assert len(report['resource_gates'])==6
    for gate in report['resource_gates']:
        assert gate['passed'] and gate['available_RAM_bytes']>=gate['minimum_RAM_bytes']==2684354560
        assert gate['minimum_free_F_bytes']==gate['ungenerated_retained_outputs']*800000008+536870912
        assert gate['free_F_bytes']>=gate['minimum_free_F_bytes']
    paths=[Path(ref['output']),Path(proved['output'])]; hashes=[hashlib.sha256(),hashlib.sha256()]; total=0
    assert all(p.stat().st_size==800000008 for p in paths)
    with paths[0].open('rb') as a,paths[1].open('rb') as b:
        header=a.read(8); assert header==b.read(8) and struct.unpack('<II',header)==(1,10000)
        for h in hashes: h.update(header)
        total=8
        while True:
            left,right=a.read(1024**2),b.read(1024**2)
            assert left==right, f'full-file difference at {total}'
            if not left: break
            hashes[0].update(left); hashes[1].update(right); total+=len(left)
    assert total==800000008 and hashes[0].hexdigest()==hashes[1].hexdigest()==ref['sha256']==proved['sha256']
    for name,row in plan['frozen_files'].items(): assert sha(folder/name)==row['sha256']==sha(row['origin']),name
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(folder/'report.json'),N=10000,
        independently_compared_bytes=total,full_output_sha256=hashes[0].hexdigest(),actual_VM_steps=raw['vm_steps'],proved_bound=raw['vm_budget_bound_peak'],
        fixed_default_rejects=True,optin_proved_full_original_C_identical=True,ordinary_changed=False,performance_claim=False,
        scope='Exact one original-C plus two same844 VM executions, all raw stdout/stderr and six live resource gates reviewed; independent full800MB streaming byte comparison. Proof restores completion for this source/shape; does not establish arbitrary-C coverage, default completion or speedup.')
    (ROOT/'outputs/stage2-root-vm-nested-triangular-maximum-actual.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result))
if __name__=='__main__': main()
