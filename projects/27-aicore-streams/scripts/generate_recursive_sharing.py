"""Different DAG grammar: nested fork/join with nonlocal shared ancestors."""
import hashlib
import json
import random
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def make(seed, leaves, family, retained):
    rng=random.Random(seed);ids=iter(rng.sample(range(10000,2000000000),3*leaves));nodes=[];producers=[]
    def emit(inputs,consume=False):
        ident=next(ids);duration=rng.randint(1,10000)
        work=rng.randint(80,700) if consume else rng.randint(0,20)
        output=rng.randint(0,12) if consume and retained else (0 if consume else rng.randint(20,300))
        if family=='nonlocal' and consume and producers:
            candidates=[p for p in producers if p not in inputs]
            if candidates:
                inputs=inputs+rng.sample(candidates,min(len(candidates),rng.randint(1,4)))
        rng.shuffle(inputs);nodes.append(node(ident,rng.choice(['AIC','AIV']),rng.randint(1,8),duration,work,output,inputs))
        if not consume:producers.append(ident)
        return ident
    def build(count,parent=None):
        if count==1:return emit([] if parent is None else [parent],True)
        source=emit([] if parent is None else [parent])
        split=count//2 if family=='balanced' else rng.randint(1,count-1)
        left=build(split,source);right=build(count-split,source)
        return emit([source,left,right],True)
    build(leaves);witness,T,P=serial_witness(nodes);rng.shuffle(nodes)
    x=case(f'recursive_{family}_leaves{leaves}_ret{retained}_seed{seed}',hardware(streams=8,memory=P,record=3,wait=3),nodes,T,witness)
    x['generation']=dict(seed=seed,family='recursive_fork_join_sharing',shape=family,leaves=leaves,retained_outputs=retained,
        witness_T=T,witness_peak=P,feasibility='hidden recursive emission is topological; nonlocal inputs select prior positive-output producers; no solver outcome filtering')
    return x


def main():
    seed=20301029;cases=[make(seed+l*100+f*10+r,l,family,r) for l in [16,64,256] for f,family in enumerate(['balanced','random-split','nonlocal']) for r in [0,1]]
    output=Path('data/recursive-sharing-unseen-batch29.json');output.write_text(json.dumps(dict(format='aicore-local-v1',generator_seed=seed,
        validation_scope='generated after batch29 freeze; one run each frozen28/29; no subsequent batch29 tuning',cases=cases),separators=(',',':')),encoding='utf-8')
    provenance=dict(input_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        baseline_source_sha256=hashlib.sha256(Path('research/batch28/solution.cpp').read_bytes()).hexdigest(),
        after_source_sha256=hashlib.sha256(Path('research/batch29/solution.cpp').read_bytes()).hexdigest(),records=len(cases),
        nodes_range=[min(len(x['nodes']) for x in cases),max(len(x['nodes']) for x in cases)])
    Path('reports/recursive-sharing-unseen-batch29-provenance.json').write_text(json.dumps(provenance,indent=2));print(provenance)


if __name__=='__main__':main()
