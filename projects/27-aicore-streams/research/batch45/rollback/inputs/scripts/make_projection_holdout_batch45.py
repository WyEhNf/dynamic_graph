"""Unfiltered fresh retention graphs; no solver-driven seed selection."""
import hashlib,json
from pathlib import Path
from generate_irregular_consumers import irregular_case
from generate_frontier_cases import resource_witness
def main():
    cases=[]
    for q in range(48):
        seed=203451001+q;count=[8,12,24,48][q%4];family=['local','dense','global'][q//4%3]
        c=irregular_case(seed,count,family,1)
        # Existing constructive stage witness retained. Changes derive solely
        # from predeclared index, not whether an implementation can solve it.
        for v in c['nodes']:
            if not v['inputs']:v['output_memory']=(q%4)*3
            if v['workspace_memory']>100 and q%5==0:v['workspace_memory']+=47
        c['hardware']['event_record_time']=[0,3,500][q%3];c['hardware']['event_wait_time']=[0,2,100][q%3]
        # Derive the new exact capacity with an unconstrained-memory replay;
        # retaining the previous smaller capacity would block the witness.
        c['hardware']['memory_limit']=2**63-1
        duration,peak=resource_witness(c['hardware'],c['nodes'],c['witness_plan'])
        c['hardware']['memory_limit']=peak;c['deadline_us']=duration;c['name']=f'projection_retention_seed{seed}'
        c['generation']=dict(seed=seed,family='fresh_retention_closures',connection=family,stages=count,root_output=(q%4)*3,workspace_offset=47 if q%5==0 else 0,witness_T=duration,witness_peak=peak,feasibility='Independent Python original direct-user event replay of predeclared constructive order')
        cases.append(c)
    p=Path('data/projection-retention-heldout-batch45.json');p.write_text(json.dumps(dict(format='aicore-local-v1',cases=cases)),encoding='utf-8')
    print(len(cases),'unfiltered fresh seed graphs',hashlib.sha256(p.read_bytes()).hexdigest())
if __name__=='__main__':main()
