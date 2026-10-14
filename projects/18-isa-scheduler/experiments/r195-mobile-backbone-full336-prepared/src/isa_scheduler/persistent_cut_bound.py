"""All-order COPY lower bound between two forced DAG anchors.

Every selected identity is an ancestor of A and has a consumer strictly after
B, where A precedes B. Identities persist across every descendant-of-A AND
ancestor-of-B original node. Distinct physical ages have range k*(W-k);
each original emission adds k and each own COPY reduces at most W-k.
Original identities once, COPY-only; no aliases/recompute/rereads/spill.
"""
from time import perf_counter
from .model import BudgetExceeded,InvalidBlock
from .raw_pure import dependencies

def _closure(args,deadline):
 n=len(args);users=[[]for _ in args];masks=[0]*n;anc=[0]*n;desc=[0]*n;future=[0]*n
 for i,sources in enumerate(args):
  if i%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Persistent-cut closure budget exhausted')
  for source in set(sources):
   users[source].append(i);masks[i]|=1<<source;anc[i]|=(1<<source)|anc[source]
 for i in range(n-1,-1,-1):
  if i%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Persistent-cut reverse closure budget exhausted')
  for user in users[i]:desc[i]|=(1<<user)|desc[user];future[i]|=masks[user]|future[user]
 return users,anc,desc,future

def _pure_names(rows):
 if any(row['op']not in ('GET','SET','ADD','MULW')for row in rows):return False
 reads=[r['reg']for r in rows if r['op']=='GET'];writes=[r['reg']for r in rows if r['op']=='SET']
 return len(set(reads))==len(reads)and len(set(writes))==len(writes)and not set(reads)&set(writes)

def persistent_cut_bound(block,*,time_budget_ms=250,max_nodes=8192):
 if time_budget_ms<=0:raise ValueError('Positive persistent-cut budget required')
 n=len(block.instructions)
 if n>max_nodes or block.memory_order!='hazard' or any(node.order_deps for node in block.instructions):return None
 rows=[{'op':node.op,'reg':node.reg}for node in block.instructions]
 if not _pure_names(rows):return None
 args=[node.args for node in block.instructions];counts=[0]*n
 for sources in args:
  for source in set(sources):counts[source]+=1
 shared=[i for i,count in enumerate(counts)if count>1]
 if not shared:return None
 started=perf_counter();deadline=started+time_budget_ms/1000
 users,anc,desc,future=_closure(args,deadline);shared_mask=sum(1<<i for i in shared)
 arithmetic=[i for i,node in enumerate(block.instructions)if node.op in ('ADD','MULW')]
 if not arithmetic:return None
 sample={arithmetic[min(len(arithmetic)-1,k*len(arithmetic)//32)]for k in range(32)}
 before=sample|set(arithmetic[:8]);after=sample|set(arithmetic[-16:])
 for source in sorted(shared,key=lambda i:(-counts[i],i))[:32]:
  before.add(users[source][0]);after.update(args[users[source][-1]])
 before=sorted(before);after=sorted(after);best=0;witness=None;tested=0;budget_limited=False
 for a in before:
  for b in after:
   tested+=1
   if tested%128==0 and perf_counter()>=deadline:
    budget_limited=True;break
   if not (anc[b]>>a)&1:continue
   persistent=anc[a]&future[b]&shared_mask;k=min(persistent.bit_count(),block.window-1)
   if not k:continue
   inner=(desc[a]&anc[b]).bit_count();slack=block.window-k;lower=max(0,(k*inner-k*slack+slack-1)//slack)
   if lower>best:
    selected=[]
    while persistent and len(selected)<k:
     bit=persistent&-persistent;selected.append(bit.bit_length()-1);persistent^=bit
    best=lower;witness={'before':a,'after':b,'identities':selected,'forced_inner_nodes':inner,'age_sum_range':k*slack}
  if budget_limited:break
 if not witness:return None
 return {'kind':'forced_dag_persistent_identity_age_sum','window':block.window,'copy_lower_bound':best,'witness':witness,
         'scope':'all topological orders; pure unique/disjoint GET/SET names; original identities once; COPY-only; no aliases/recompute/rereads/spill',
         'proposal_ms':(perf_counter()-started)*1000,'anchor_pairs':tested,'proposal_budget_limited':budget_limited}

def check_persistent_cut_certificate(data,certificate):
 # Rebuild ancestry directly from raw JSON. Do not call the proposer, model,
 # source ranking or cached closures; only validate the supplied two anchors.
 args=dependencies(data);rows=data['instructions']
 if not _pure_names(rows):raise InvalidBlock('Pure unique/disjoint registers required')
 witness=certificate.get('witness');window=2**data['bit_width'];claimed=certificate.get('copy_lower_bound')
 if certificate.get('kind')!='forced_dag_persistent_identity_age_sum' or certificate.get('window')!=window or type(claimed)is not int or claimed<0 or not isinstance(witness,dict):raise InvalidBlock('Invalid persistent-cut certificate')
 a=witness.get('before');b=witness.get('after');selected=witness.get('identities')
 if type(a)is not int or type(b)is not int or not 0<=a<b<len(rows) or not isinstance(selected,list)or any(type(i)is not int or not 0<=i<len(rows)for i in selected):raise InvalidBlock('Invalid persistent-cut anchors/identities')
 if not 0<len(selected)<window or len(set(selected))!=len(selected):raise InvalidBlock('Distinct persistent identities fewer than W required')
 def ancestors(index):
  seen=set();stack=list(args[index])
  while stack:
   i=stack.pop()
   if i not in seen:seen.add(i);stack.extend(args[i])
  return seen
 users=[[]for _ in rows]
 for i,sources in enumerate(args):
  for source in set(sources):users[source].append(i)
 def descendants(index):
  seen=set();stack=list(users[index])
  while stack:
   i=stack.pop()
   if i not in seen:seen.add(i);stack.extend(users[i])
  return seen
 before_anc=ancestors(a);after_anc=ancestors(b);after_desc=descendants(b)
 if a not in after_anc or not set(selected)<=before_anc or any(not set(users[i])&after_desc for i in selected):raise InvalidBlock('Persistent identities not forced across anchors')
 inner=len(descendants(a)&after_anc);k=len(selected);slack=window-k;observed=max(0,(k*inner-k*slack+slack-1)//slack)
 if witness.get('forced_inner_nodes')!=inner or witness.get('age_sum_range')!=k*slack or claimed>observed:raise InvalidBlock('Persistent-cut inequality not established')
 return {'verified_global_copy_lower_bound':observed,'scope':'all topological orders under original-once distinct-identity COPY-only model'}
