"""Root audit of same844/true-C maximum triangle scope and remaining-output gates."""
import ast,json,time,struct
from pathlib import Path
from review_stage2_vm_nested_next_sources import ROOT,P,D,read,sha
def main():
    folder=D/'triangular-maximum';plan=read(folder/'run-plan.json')
    assert sha(folder/'run-plan.json')=='315f51596e989490378e85d1766039f3d84c23608a966fdfe06f7a843036255e'
    for name,row in plan['frozen_files'].items():
        assert sha(folder/name)==row['sha256']==sha(row['origin']) and (folder/name).stat().st_size==row['bytes']
        if name.startswith('runner-source/') and name.endswith('.py'):ast.parse((folder/name).read_text(encoding='utf-8'))
    assert Path(plan['input']).stat().st_size==800000008 and sha(plan['input'])==plan['input_sha256']
    with Path(plan['input']).open('rb')as stream:assert struct.unpack('<II',stream.read(8))==(1,10000)
    assert sha(folder/'runtime.exe')=='844c974948ac7e34d0459c05fa95c30bb6da2c4608a165f49a86586d42e64944'
    assert sha(folder/'oracle.exe')=='c8b0ede2ebd6871cf9f8d1afd3a0527cc313fe352fc56a328e468ca16768b8bc'
    assert sha(folder/'source.c')==sha(plan['original_harness_include_path'])==plan['source_sha256']
    assert plan['expected_original_VM_steps']==14*10000**2+3*10000+9==1400030009
    assert plan['expected_proved_bound']==28*10000**2-11*10000+9==2799890009
    assert plan['minimum_fresh_RAM_bytes']==2684354560 and plan['disk_reserve_bytes']==536870912
    assert plan['disk_gate_schedule']==dict(original_C_launch=2136870928,fixed_rejection_launch=1336870920,proved_launch=1336870920,after_candidate_reserve=536870912)
    assert not plan['explicit_vm_step_limit'] and not plan['performance_claim'] and not plan['ordinary_or_default_change']
    assert plan['launch_order']==['actual-original-C-oracle','GNUauto-fixed1e9-rejection','GNUauto-proved-full-output']
    result=dict(passed=True,reviewed_unix=time.time(),plan_sha256=sha(folder/'run-plan.json'),frozen_files=len(plan['frozen_files']),N=10000,expected_steps=1400030009,expected_bound=2799890009,full_output_bytes=800000008,
        authorization='Execute exactly one frozen sequential originalC/newtriangle800MB reference, fixed1e9 rejection and sameGNUauto-proved full800MB run; fresh2.5GiBRAM and remaining-output+512MiB disk gates at everylaunch. Preserve failures, no restart/Gram/backend expansion/default change.',
        scope='Actual original source/harness/accepted GCC binary, fullPROGRAM48 metadata/same844 and207 frozen artifacts verified. HighN25pureanalysis bounds do not replace this run. Actuallarge outputs/fixed rejection remain unproven; no compute speedup claim from reject-vs-success.')
    (ROOT/'outputs/stage2-root-vm-nested-triangular-maximum-plan.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
