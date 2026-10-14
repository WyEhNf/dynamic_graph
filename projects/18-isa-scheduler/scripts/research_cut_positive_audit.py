"""Predeclared positive persistent-cut cases across all four windows.

The graphs have 2..3 initial roots and a shared persistent chain, so the number
of original nodes can exceed the ordinary small-graph oracle limit while their
ready frontier stays narrow. All Dijkstra states and actions remain exact.
"""
import argparse,hashlib,json,random
from collections import Counter
from pathlib import Path
from time import perf_counter
from research_raw_cut_oracle import oracle,ROOT
from isa_scheduler.persistent_cut_bound import persistent_cut_bound,check_persistent_cut_certificate
from isa_scheduler.model import parse_block
from isa_scheduler.evaluation import fingerprint

def generate(seed,bits,k):
 rng=random.Random(seed);rows=[]
 def emit(op,args=(),reg=None):
  i=len(rows);row={'id':i,'op':op}
  if args:row['inputs']=[f't#{i-s}'for s in args]
  if reg is not None:row['reg']=reg
  rows.append(row);return i
 roots=[emit('GET',reg=f'r{i}')for i in range(k)]
 other=emit('GET',reg='private')if k==1 else roots[1]
 value=emit('ADD',(roots[0],other))
 for j in range(2**bits+rng.randint(2,6)):
  source=roots[j%k];args=(value,source)if rng.randrange(2)else(source,value)
  value=emit(rng.choice(('ADD','MULW')),args)
 for source in roots:value=emit('ADD',(value,source))
 emit('SET',(value,),'out')
 return {'block_id':f'positive-cut-{seed}','bit_width':bits,'instructions':rows}

def main():
 p=argparse.ArgumentParser();p.add_argument('--round',required=True);p.add_argument('--samples',type=int,default=24);p.add_argument('--seed',type=int,default=7800001);a=p.parse_args()
 folder=ROOT/'experiments'/a.round;folder.mkdir(exist_ok=False);rows=[];corpus=[];tick=perf_counter();violations=[]
 for bits in(2,3,4,5):
  for k in(1,2):
   for sample in range(a.samples):
    seed=a.seed+len(rows);data=generate(seed,bits,k);certificate=persistent_cut_bound(parse_block(data),time_budget_ms=1000)
    if not certificate:raise ValueError('Predeclared positive case unexpectedly has no certificate')
    bound=check_persistent_cut_certificate(data,certificate)['verified_global_copy_lower_bound'];result=oracle(data,time_budget_ms=200,max_states=200000)
    row={'sha256':fingerprint(data),'seed':seed,'bit_width':bits,'persistent_roots':k,'nodes':len(data['instructions']),'lower':bound,'certificate':certificate,**result};rows.append(row);corpus.append({'family':f'persistent_{k}','seed':seed,'input':data})
    if result['status']=='optimal'and bound>result['copies']:violations.append(row)
  print(json.dumps({'completed':len(rows),'elapsed_seconds':perf_counter()-tick}),flush=True)
 payload=''.join(json.dumps(case,separators=(',',':'))+'\n'for case in corpus);(folder/'inputs.jsonl').write_text(payload,encoding='utf-8')
 report={'count':len(rows),'statuses':dict(Counter(r['status']for r in rows)),'positive_complete':sum(r['status']=='optimal'for r in rows),'violations':violations,
         'elapsed_seconds':perf_counter()-tick,'scope':'full raw identity age-state Dijkstra on narrow-frontier positive-bound instances; no hidden state/beam truncation; budget cases unknown',
         'corpus_sha256':hashlib.sha256((folder/'inputs.jsonl').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'oracle_source_sha256':hashlib.sha256((ROOT/'scripts/research_raw_cut_oracle.py').read_bytes()).hexdigest(),'records':rows}
 (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k!='records'}));return int(bool(violations))
if __name__=='__main__':raise SystemExit(main())
