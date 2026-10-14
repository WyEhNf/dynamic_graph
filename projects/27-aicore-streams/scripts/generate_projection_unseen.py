"""Frozen batch30 validation with new widths and independent duration profiles."""
import hashlib
import json
import random
from pathlib import Path
from generate_structural_blind import make
from generate_cases import serial_witness


def main():
    seed=20311030;cases=[]
    for count in [14,18]:
        for f,family in enumerate(['local','dense']):
            for retained in [0,1]:
                for duration_profile in [0,1]:
                    s=seed+count*100+f*10+retained+duration_profile*2000
                    x=make(s,count,family,retained,'high-fanout')
                    if duration_profile:
                        rng=random.Random(s+99)
                        for v in x['nodes']:v['exec_time']=rng.randint(1,100)
                        by_id={v['id']:v for v in x['nodes']};order=[by_id[t['op_id']] for stream in x['witness_plan']['streams'] for t in stream['tasks']]
                        witness,T,P=serial_witness(order);x['witness_plan']=witness;x['deadline_us']=T;x['hardware']['memory_limit']=P
                        x['generation'].update(witness_T=T,witness_peak=P)
                    k=len(cases);x['hardware'].update(aic_core_num=[8,128][k%2],aiv_core_num=[128,8][k%2],stream_num=[4,16][k%2],event_record_time=[0,3,1000000][k%3],event_wait_time=[0,3,1000000][k%3])
                    profile='random-duration' if duration_profile else 'role-duration'
                    x['name']=x['name'].replace('blind_','projection_unseen_')+'_'+profile;x['generation']['duration_profile']=profile
                    cases.append(x)
    output=Path('data/projection-unseen-batch30.json');output.write_text(json.dumps(dict(format='aicore-local-v1',generator_seed=seed,
        validation_scope='generated after batch30 freeze; one frozen29/30 run, no subsequent batch30 tuning; distinct seeds for duration profiles',cases=cases),separators=(',',':')),encoding='utf-8')
    provenance=dict(input_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        shared_generator_sha256=hashlib.sha256(Path('scripts/generate_structural_blind.py').read_bytes()).hexdigest(),
        baseline_source_sha256=hashlib.sha256(Path('research/batch29/solution.cpp').read_bytes()).hexdigest(),
        after_source_sha256=hashlib.sha256(Path('research/batch30/solution.cpp').read_bytes()).hexdigest(),records=16,
        nodes_range=[min(len(x['nodes']) for x in cases),max(len(x['nodes']) for x in cases)])
    Path('reports/projection-unseen-batch30-provenance.json').write_text(json.dumps(provenance,indent=2));print(provenance)


if __name__=='__main__':main()
