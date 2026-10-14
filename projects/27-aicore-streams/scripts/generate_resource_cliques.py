"""Analytic optima for half-resource cliques and exact-half negative controls."""
import hashlib
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def main():
    seed=20321031;cases=[]
    for n in [16,512,10000]:
        for p,profile in enumerate(['aic-heavy','aiv-heavy','memory-heavy','exact-half']):
            s=seed+n*100+p;rng=random.Random(s);ids=rng.sample(range(10000,2000000000),n)
            h=hardware(streams=256,memory=1000000000,record=0,wait=0);h.update(aic_core_num=8 if profile in ['aic-heavy','exact-half'] else 128,aiv_core_num=128)
            nodes=[]
            for ident in ids:
                kind='AIV' if profile=='aiv-heavy' else 'AIC';cores={'aic-heavy':5,'aiv-heavy':65,'memory-heavy':1,'exact-half':4}[profile]
                dur=1000000000 if profile in ['aiv-heavy','memory-heavy'] else (7 if profile=='exact-half' else rng.randint(1,1000))
                nodes.append(node(ident,kind,cores,dur,600000000 if profile=='memory-heavy' else 0,0))
            if profile=='exact-half':
                witness={'streams':[{'tasks':[{'op_id':v['id'],'wait_before':[],'record_after':-1} for v in nodes[k::2]]} for k in [0,1]]}
                T=7*n//2;peak=0;proof='two independent requests use exactly all eight AIC cores, so equal-duration pairs attain core-area lower bound'
            else:
                witness,T,peak=serial_witness(nodes);proof='each Compute uses more than half of one shared resource, hence all intervals pairwise disjoint; serial witness attains sum durations and mandatory max allocation'
            rng.shuffle(nodes);x=case(f'resource_clique_{profile}_n{n}_seed{s}',h,nodes,T,witness)
            x['generation']=dict(seed=s,family='analytic_resource_clique',profile=profile,optimal_T=T,optimal_peak=peak,proof=proof,witness_T=T,witness_peak=peak)
            cases.append(x)
    output=Path('data/resource-cliques-batch31.json');output.write_text(json.dumps(dict(format='aicore-local-v1',generator_seed=seed,cases=cases),separators=(',',':')),encoding='utf-8')
    provenance=dict(input_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),records=12,
        baseline_source_sha256=hashlib.sha256(Path('research/batch30/solution.cpp').read_bytes()).hexdigest(),source_freeze_scope='planned analytic controls, constructed from theorem before examining solver outcomes; not random unseen performance distribution')
    Path('reports/resource-cliques-batch31-provenance.json').write_text(json.dumps(provenance,indent=2));print(provenance)


if __name__=='__main__':main()
