"""Delay GET births and complete disjoint single-constant spine groups.

Strict pure recognition, no extra GET/alias/recompute/spill or operation deletion.
All arithmetic values have a single consumer, the sole shared identities are GET
roots. Each branch uses one common GET at every arithmetic step and at most one
private GET at its first step, ending in a dedicated SET. Shared-root components
can be completed separately; only one common root is live at a time.
This proves eligibility of the proposed orders, NOT global COPY optimality.
"""
from collections import defaultdict
from time import perf_counter
from .local_order import emit_order
from .model import BudgetExceeded,InfeasibleSchedule

def recognize_root_spines(block,*,deadline=float('inf'),prepared=None):
 if block.memory_order!='hazard':return None
 nodes=block.instructions
 if any(node.op not in ('GET','SET','ADD','MULW')for node in nodes):return None
 reads=[node.reg for node in nodes if node.op=='GET'];writes=[node.reg for node in nodes if node.op=='SET']
 if len(set(reads))!=len(reads)or len(set(writes))!=len(writes)or set(reads)&set(writes):return None
 if prepared is not None and prepared.block is not block:raise ValueError('Graph belongs to another block')
 # Recognition needs only distinct data consumers. Do not construct general
 # scheduling ranks, hazard successor heaps or demand estimates for this shape.
 if prepared is not None:
  args_unique=prepared.args_unique;counts=[len(users)for users in prepared.data_users]
 else:
  args_unique=[frozenset(node.args)for node in nodes];counts=[0]*len(nodes)
  for i,args in enumerate(args_unique):
   if i%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Root-spine consumer scan budget exhausted')
   for source in args:counts[source]+=1
 if any((node.op in ('ADD','MULW')and counts[node.index]!=1)or(node.op=='SET'and counts[node.index])for node in nodes):return None
 groups=defaultdict(list);covered=set();private_owners={};common_roots=set()
 for terminal in nodes:
  if terminal.index%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Root-spine recognition budget exhausted')
  if terminal.op!='SET':continue
  current=terminal.args[0];reverse=[];intersection=None
  while nodes[current].op in ('ADD','MULW'):
   if current in covered:return None
   covered.add(current);reverse.append(current);args=args_unique[current]
   gets={s for s in args if nodes[s].op=='GET'}
   intersection=gets if intersection is None else intersection&gets
   predecessors=[s for s in args if nodes[s].op in ('ADD','MULW')]
   if len(predecessors)>1 or any(nodes[s].op not in ('GET','ADD','MULW')for s in args):return None
   if not predecessors:break
   current=predecessors[0]
   if len(reverse)%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Root-spine path recognition budget exhausted')
  if not reverse or not intersection:return None
  chain=list(reversed(reverse));common=min(intersection,key=lambda s:(-counts[s],s));common_roots.add(common)
  private=set(args_unique[chain[0]])-{common}
  if len(private)>1 or any(nodes[s].op!='GET' or counts[s]!=1 for s in private):return None
  for stage,i in enumerate(chain):
   expected={common,chain[stage-1]} if stage else {common}|private
   if args_unique[i]!=expected:return None
  if private:
   root=next(iter(private))
   if root in private_owners:return None
   private_owners[root]=terminal.index
  groups[common].append({'private':tuple(private),'arithmetic':tuple(chain),'terminal':terminal.index})
 if not groups or len(covered)!=sum(node.op in ('ADD','MULW')for node in nodes)or common_roots&private_owners.keys():return None
 return {'groups':dict(groups)}

def root_spine_orders(block,plan):
 for policy in ('long_first','long_last','original'):
  order=[];emitted=set()
  for root,branches in sorted(plan['groups'].items()):
   order.append(root);emitted.add(root)
   if policy=='long_first':branches=sorted(branches,key=lambda b:(-len(b['arithmetic']),b['terminal']))
   elif policy=='long_last':branches=sorted(branches,key=lambda b:(len(b['arithmetic']),b['terminal']))
   for branch in branches:
    order.extend(branch['private']);emitted.update(branch['private']);order.extend(branch['arithmetic']);order.append(branch['terminal'])
  order.extend(node.index for node in block.instructions if node.op=='GET'and node.index not in emitted)
  yield policy,order

def schedule_root_spines(block,*,time_budget_ms=100,prepared=None,plan=None):
 if time_budget_ms<=0:raise ValueError('Positive root-spine budget required')
 started=perf_counter();deadline=started+time_budget_ms/1000
 if plan is None:plan=recognize_root_spines(block,deadline=deadline,prepared=prepared)
 if plan is None:raise InfeasibleSchedule('root_spines requires complete pure single-common-GET arithmetic spines; no global proof')
 best=None;attempts=[];seen=set()
 for policy,order in root_spine_orders(block,plan):
  signature=tuple(order)
  if signature in seen:continue
  seen.add(signature)
  try:
   if best is None:candidate=emit_order(block,order,deadline=deadline)
   else:
    cost=emit_order(block,order,deadline=deadline,cutoff=best['stats']['inserted_copy_count'],materialize=False)
    if cost is None:attempts.append({'policy':policy,'outcome':'no_fixed_order_improvement'});continue
    candidate=emit_order(block,order,deadline=deadline)
   if candidate is None:attempts.append({'policy':policy,'outcome':'fixed_order_failed'});continue
   attempts.append({'policy':policy,'outcome':'emitted','copies':candidate['stats']['inserted_copy_count']});best=candidate
  except BudgetExceeded:
   attempts.append({'policy':policy,'outcome':'budget_exhausted'})
   if best is None:raise
   break
 if best is None:raise InfeasibleSchedule('Root-spine proposals failed; not a whole-problem proof')
 best['stats'].update(strategy='root_spines',root_spine_groups=len(plan['groups']),root_spine_branches=sum(len(v)for v in plan['groups'].values()),root_spine_attempts=attempts,elapsed_ms=(perf_counter()-started)*1000,
                      root_spine_scope='original identities once, original ordered arguments, complete independent single-common-root spines, no GET duplication or aliases')
 return best
