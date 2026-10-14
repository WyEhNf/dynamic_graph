"""Root review of actual allocation-free high-N proof observations."""
import json,time
from review_stage2_vm_nested_next_sources import ROOT,P,D,read,sha
def main():
    f=D/'analysis-only-acceptance';m=read(f/'manifest.json');r=read(D/'analysis-only/report.json');plan=read(D/'analysis-only/run-plan.json');compiled=read(D/'analysis-only/compile-report.json')
    assert m['passed'] and r['passed'] and r['status']=='complete' and compiled['passed'] and compiled['actual_exit_code']==0
    assert sha(D/'analysis-only/report.json')=='c13c7e9663c8b4b81e01caccdfa22646f1976e173c34585d5532e96c4e4a36ce'
    for name,row in m['frozen_files'].items():assert sha(f/name)==row['sha256']==sha(row['origin'])
    assert sha(D/'analysis-only/probe.exe')==r['probe_EXE_sha256']==compiled['EXE_sha256']
    assert compiled['command']==plan['compile_command']
    assert len(r['records'])==len(r['resource_gates'])==25;positive=unknown=0
    formula={'nested-rect-strides':lambda n:9+17*(n//2)+30*(n//2)*((n+2)//3), 'nested-triangular':lambda n:28*n*n-11*n+9,'nested-gram-three':lambda n:30*n**3+28*n*n+17*n+9}
    for row,case,gate in zip(r['records'],plan['cases'],r['resource_gates']):
        assert (row['source'],row['N'])==(case['source'],case['N']) and row['actual_exit_code']==0 and gate['passed']
        assert sha(row['raw_stdout'])==row['raw_stdout_sha256'] and sha(row['raw_stderr'])==row['raw_stderr_sha256'] and not Path(row['raw_stderr']).read_bytes()
        raw=read(row['raw_stdout'])
        for k,v in raw.items():assert row[k]==v
        assert raw['matrix_allocations']==raw['VM_executions']==raw['native_executions']==0
        assert raw['first_work']+raw['nested_work']==raw['shared_work']<=250000
        assert raw['remaining_after_first']==250000-raw['first_work'] and raw['nested_work']<=raw['remaining_after_first']
        assert raw['effective_cap']==(max(1000000000,raw['bound']) if raw['proved'] else 1000000000)
        assert row['resource_samples']>0 and row['process_peak_working_set_bytes']>0
        if row['source'] in formula:
            assert raw['proved'] and raw['bound']==formula[row['source']](row['N'])==case['static_predicted_bound'];positive+=1
        else:assert not raw['proved'];unknown+=1
    assert (positive,unknown)==(15,10)
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(D/'analysis-only/report.json'),acceptance_sha256=sha(f/'manifest.json'),frozen_files=len(m['frozen_files']),actual_compile_exit=0,actual_analysis_exit=0,observations=25,positive_bounds=positive,unknown=unknown,max_shared_work=max(x['shared_work']for x in r['records']),N10000_bounds={label:fn(10000)for label,fn in formula.items()},scope='Actual matchingABI probe25 raw observations/full259freeze/strictFP flags and independently recomputed highN bounds verified. No Matrix/C/VM allocation or execution; these are analysis bounds, not highN runtime correctness or performance.')
    (ROOT/'outputs/stage2-root-vm-nested-analysis-actual.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
from pathlib import Path
if __name__=='__main__':main()
