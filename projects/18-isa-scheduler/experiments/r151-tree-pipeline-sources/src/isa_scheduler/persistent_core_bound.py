"""Global persistent-identity age bound on incomparable forced core nodes.

For selected roots S, a core node is after EVERY root and before a forced
future direct consumer of EVERY root. All core nodes lie between the last
selected birth and the first selected last-use in any original-once order.
Only take MAX of certificates; overlapping cores cannot be added.
"""
from itertools import combinations
from time import perf_counter
from .persistent_cut_bound import _closure,_pure_names
from .raw_pure import dependencies
from .model import InvalidBlock,BudgetExceeded

def persistent_core_bound(block,*,time_budget_ms=250,max_nodes=8192,max_subsets=1024):
 n=len(block.instructions)
 if n>max_nodes or block.memory_order!='hazard' or any(node.order_deps for node in block.instructions):return None
 if not _pure_names([{'op':node.op,'reg':node.reg}for node in block.instructions]):return None
 tick=perf_counter();deadline=tick+time_budget_ms/1000;args=[node.args for node in block.instructions]
 users,anc,desc,future=_closure(args,deadline)
 roots=sorted((i for i,node in enumerate(block.instructions)if node.op=='GET'and len(users[i])>1),key=lambda i:(-len(users[i]),i))[:12]
 best=0;witness=None;tested=0;limited=False
 for k in range(1,min(len(roots),block.window-1,6)+1):
  for selected in combinations(roots,k):
   if tested>=max_subsets or perf_counter()>=deadline:limited=True;break
   tested+=1;mask=sum(1<<i for i in selected)
   inner=sum((anc[i]&mask)==mask and(future[i]&mask)==mask for i in range(n))
   slack=block.window-k;lower=max(0,(k*inner-k*slack+slack-1)//slack)
   if lower>best:best=lower;witness={'identities':list(selected),'forced_core_nodes':inner,'age_sum_range':k*slack}
  if limited:break
 if witness is None:return None
 return {'kind':'global_persistent_core_age_sum','window':block.window,'copy_lower_bound':best,'witness':witness,
         'scope':'all original-once orders; pure unique/disjoint GET/SET; distinct original identities; COPY-only; no alias/recompute/reread/spill',
         'proposal_ms':(perf_counter()-tick)*1000,'candidate_subsets':tested,'proposal_budget_limited':limited}

def check_persistent_core_certificate(data,certificate):
 args=dependencies(data);rows=data['instructions'];w=2**data['bit_width'];claim=certificate.get('copy_lower_bound');proof=certificate.get('witness')
 if not _pure_names(rows)or certificate.get('kind')!='global_persistent_core_age_sum'or certificate.get('window')!=w or type(claim)is not int or claim<0 or not isinstance(proof,dict):raise InvalidBlock('Invalid persistent-core certificate')
 selected=proof.get('identities')
 if not isinstance(selected,list)or not 0<len(selected)<w or any(type(i)is not int or not 0<=i<len(rows)or rows[i]['op']!='GET'for i in selected)or len(set(selected))!=len(selected):raise InvalidBlock('Distinct selected GET identities required')
 users=[[]for _ in rows]
 for i,sources in enumerate(args):
  for s in set(sources):users[s].append(i)
 def walk(starts,edges):
  stack=list(starts);seen=set()
  while stack:
   i=stack.pop()
   if i not in seen:seen.add(i);stack.extend(edges[i])
  return seen
 forced=None
 for root in selected:
  after_birth=walk(users[root],users)
  # Strict ancestors of any direct consumer; a consumer itself is not
  # automatically before that use. This excludes the last-use endpoint.
  before_last_use=walk((s for u in users[root]for s in args[u]),args)
  both=after_birth&before_last_use;forced=both if forced is None else forced&both
 inner=len(forced);k=len(selected);slack=w-k;lower=max(0,(k*inner-k*slack+slack-1)//slack)
 if proof.get('forced_core_nodes')!=inner or proof.get('age_sum_range')!=k*slack or claim>lower:raise InvalidBlock('Persistent-core inequality not established')
 return {'verified_global_copy_lower_bound':lower,'scope':'all topological original-once COPY-only identity orders; selected roots share one birth-to-last-use interval'}
