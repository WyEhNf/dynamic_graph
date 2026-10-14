"""Independent raw-JSON all-order age-state oracle for small proof audits.

No scheduler, parsed Block, PreparedGraph, emitter, or search state is used.
Canonical state = completed original bitmask and latest live identity ages.
All ready originals and all live-identity COPY actions are explored by Dijkstra.
Only a drained queue proves infeasibility; time/state limits are unknown.
"""
import argparse,hashlib,heapq,json,random,sys
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.persistent_cut_bound import persistent_cut_bound,check_persistent_cut_certificate
from isa_scheduler.model import parse_block
from isa_scheduler.evaluation import fingerprint

def oracle(data,*,max_states=100000,time_budget_ms=200):
 n=len(data['instructions']);w=2**data['bit_width'];deps=[];users=[0]*n;full=(1<<n)-1
 for i,row in enumerate(data['instructions']):
  args=tuple(i-int(token[2:])for token in row.get('inputs',[]))
  if any(not 0<=s<i for s in args):raise ValueError('Bad raw original reference')
  deps.append(args)
  for s in set(args):users[s]|=1<<i
 start=(0,(0,)*n);dist={start:0};heap=[(0,*start)];expanded=0;tick=perf_counter();deadline=tick+time_budget_ms/1000
 while heap:
  cost,mask,ages=heapq.heappop(heap);state=(mask,ages)
  if dist.get(state)!=cost:continue
  if mask==full:return {'status':'optimal','copies':cost,'states':len(dist),'expanded':expanded,'elapsed_ms':(perf_counter()-tick)*1000}
  expanded+=1
  if expanded%128==1 and(perf_counter()>=deadline or len(dist)>max_states):return {'status':'unknown_budget','states':len(dist),'expanded':expanded,'elapsed_ms':(perf_counter()-tick)*1000}
  live=[s for s,age in enumerate(ages)if age]
  actions=[(i,False)for i in range(n)if not(mask>>i)&1 and all((mask>>s)&1 and ages[s]>0 for s in deps[i])]
  actions.extend((s,True)for s in live)
  for i,copy in actions:
   next_mask=mask if copy else mask|(1<<i);next_ages=[0]*n;valid=True
   for s in live:
    if users[s]&~next_mask:
     age=1 if copy and s==i else ages[s]+1
     if age>w:valid=False;break
     next_ages[s]=age
   if not valid:continue
   if not copy and users[i]&~next_mask:next_ages[i]=1
   next_state=(next_mask,tuple(next_ages));next_cost=cost+int(copy)
   if next_cost<dist.get(next_state,float('inf')):
    dist[next_state]=next_cost;heapq.heappush(heap,(next_cost,*next_state))
 return {'status':'proven_infeasible_identity_model','states':len(dist),'expanded':expanded,'elapsed_ms':(perf_counter()-tick)*1000}

def generated(seed,bits,mode):
 rng=random.Random(seed);rows=[];args=[]
 def add(op,sources=(),reg=None):
  i=len(rows);row={'id':i,'op':op}
  if reg is not None:row['reg']=reg
  if sources:row['inputs']=[f't#{i-s}'for s in sources]
  rows.append(row);args.append(tuple(sources));return i
 roots=[add('GET',reg=f'r{i}')for i in range(rng.randint(2,4))]
 for step in range(rng.randint(4,8)):
  candidates=list(range(len(rows)))
  if mode=='spine':sources=(len(rows)-1,rng.choice(roots))
  elif mode=='anchor':sources=(len(rows)-1,rng.choice(candidates))if step%3 else(rng.choice(roots),rng.choice(candidates))
  else:sources=tuple(rng.choice(candidates)for _ in range(2))
  add(rng.choice(('ADD','MULW')),sources)
 used={s for pair in args for s in pair};leaves=[i for i in range(len(rows))if i not in used]
 for j,i in enumerate(leaves):add('SET',(i,),f'out{j}')
 return {'block_id':f'raw-cut-{mode}-{seed}','bit_width':bits,'instructions':rows}

def main():
 p=argparse.ArgumentParser();p.add_argument('--round',required=True);p.add_argument('--count',type=int,default=1200);p.add_argument('--seed',type=int,default=7500001);p.add_argument('--budget-ms',type=float,default=100);a=p.parse_args()
 folder=ROOT/'experiments'/a.round;folder.mkdir(exist_ok=False);records=[];corpus=[];started=perf_counter();violations=[]
 for index in range(a.count):
  seed=a.seed+index;mode=('spine','anchor','random')[index%3];bits=2+(index//3)%4;data=generated(seed,bits,mode);certificate=persistent_cut_bound(parse_block(data),time_budget_ms=1000)
  lower=check_persistent_cut_certificate(data,certificate)['verified_global_copy_lower_bound']if certificate else 0
  result=oracle(data,time_budget_ms=a.budget_ms);item={'sha256':fingerprint(data),'seed':seed,'family':mode,'bit_width':bits,'nodes':len(data['instructions']),'lower':lower,'certificate':certificate,**result}
  corpus.append({'family':mode,'seed':seed,'input':data});records.append(item)
  if result['status']=='optimal'and lower>result['copies']:violations.append(item)
  if(index+1)%100==0:print(json.dumps({'completed':index+1,'elapsed_seconds':perf_counter()-started}),flush=True)
 from collections import Counter
 report={'count':len(records),'scope':'all ready original nodes and all live identity COPY actions; pure unique/disjoint registers; completed oracle only, budgets unknown',
         'statuses':dict(Counter(r['status']for r in records)),'positive_certificates':sum(r['lower']>0 for r in records),
         'positive_complete':sum(r['lower']>0 and r['status']=='optimal'for r in records),'violations':violations,
         'elapsed_seconds':perf_counter()-started,'records':records,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 payload=''.join(json.dumps(case,separators=(',',':'))+'\n'for case in corpus);(folder/'inputs.jsonl').write_text(payload,encoding='utf-8');report['corpus_sha256']=hashlib.sha256((folder/'inputs.jsonl').read_bytes()).hexdigest()
 (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k!='records'}));return int(bool(violations))
if __name__=='__main__':raise SystemExit(main())
