"""Post-batch28 freeze: new seed, sizes, and heterogeneous resource settings."""
import hashlib
import json
from pathlib import Path
from generate_structural_blind import make


def main():
    cases=[];seed=20291028
    for count in [16,80,160]:
        for f,family in enumerate(['local','dense']):
            for retained in [0,1]:
                x=make(seed+count*100+f*10+retained,count,family,retained,'high-fanout')
                k=len(cases);a=[4,8,16,128][k%4];b=[128,16,8,4][k%4]
                x['hardware'].update(aic_core_num=a,aiv_core_num=b,stream_num=[4,8,16][k%3],event_record_time=[0,3,1000000][k%3],event_wait_time=[0,3,1000000][k%3])
                for v in x['nodes']:v['core_num']=min(v['core_num'],a if v['core_type']=='AIC' else b)
                x['generation']['resource_variant']=dict(aic=a,aiv=b,streams=x['hardware']['stream_num'],event=x['hardware']['event_record_time'],core_clamped_to_corresponding_pool=True)
                x['name']=x['name'].replace('blind_','wide_unseen_')
                cases.append(x)
    output=Path('data/wide-unseen-batch28.json');output.write_text(json.dumps(dict(format='aicore-local-v1',generator_seed=seed,
        validation_scope='one-time batch28 frozen validation; no outcomes filtered and no batch28 tuning after results',cases=cases),separators=(',',':')),encoding='utf-8')
    provenance=dict(input_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        shared_generator_sha256=hashlib.sha256(Path('scripts/generate_structural_blind.py').read_bytes()).hexdigest(),
        baseline_source_sha256=hashlib.sha256(Path('research/batch27/solution.cpp').read_bytes()).hexdigest(),
        after_source_sha256=hashlib.sha256(Path('research/batch28/solution.cpp').read_bytes()).hexdigest(),records=12,
        nodes_range=[min(len(x['nodes']) for x in cases),max(len(x['nodes']) for x in cases)],witness='unchanged serial tasks; core clamp within pool; no events on one stream')
    Path('reports/wide-unseen-batch28-provenance.json').write_text(json.dumps(provenance,indent=2));print(provenance)


if __name__=='__main__':main()
