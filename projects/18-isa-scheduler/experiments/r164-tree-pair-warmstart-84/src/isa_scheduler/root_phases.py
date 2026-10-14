"""Delay shared-GET births across bounded open disjoint arithmetic spines.

At most W-S-1 branch states are opened, where S is total distinct shared GET
identities. This reserves a physical history slot for relay progress. It is a
restricted order proposal, not a global optimum/capacity proof. Original nodes,
ordered inputs and independent architectural GET/SET roles remain unchanged.
"""
from collections import Counter
from time import perf_counter
from .branch_copy import _branches
from .incremental import PreparedGraph
from .local_order import emit_order
from .model import BudgetExceeded,InfeasibleSchedule

def propose_root_phase_order(block,prepared,*,max_open=2,deadline=float('inf'),birth_policy='long_run'):
 branches,unused=_branches(block,prepared);nodes=block.instructions;membership=Counter(s for branch in branches for s in branch['roots'])
 shared={s for s,count in membership.items()if count>1};limit=min(max_open,block.window-len(shared)-1)
 if limit<1:raise InfeasibleSchedule('Root phase reserve does not fit; restricted policy failure only')
 prefix=[0]*len(branches);begun=set();finished=set();active=set();gets=set(unused);order=list(unused);births=0;scans=0;version=0;run_cache={}
 def missing(index):
  node=branches[index]['arithmetic'][prefix[index]]
  return {s for s in prepared.args_unique[node]if nodes[s].op=='GET'and s not in gets}
 def run(index,extra=()):
  if not extra and(index,version)in run_cache:return max(0,run_cache[index,version]-prefix[index])
  known=gets|set(extra);length=0
  for node in branches[index]['arithmetic'][prefix[index]:]:
   if any(s in shared and s not in known for s in prepared.args_unique[node]):break
   length+=1
  if not extra:run_cache[index,version]=prefix[index]+length
  return length
 while len(finished)<len(branches):
  scans+=1
  if scans%64==1 and perf_counter()>=deadline:raise BudgetExceeded('Shared-root phase ordering budget exhausted')
  ready=[i for i in active if not(missing(i)&shared)]
  if ready:index=max(ready,key=lambda i:(run(i),-i))
  else:
   options=[i for i in range(len(branches))if i not in begun and not(missing(i)&shared)]if len(active)<limit else []
   if options:index=max(options,key=lambda i:(run(i),-i));begun.add(index);active.add(index)
   else:
    candidates=list(active)or[i for i in range(len(branches))if i not in begun]
    if birth_policy=='few_uses':index=min(candidates,key=lambda i:(sum(prepared.remaining[s]for s in missing(i)&shared),-run(i,missing(i)) ,i))
    else:index=max(candidates,key=lambda i:(run(i,missing(i)),-len(missing(i)&shared),-i))
    if index not in begun:begun.add(index);active.add(index)
  node=branches[index]['arithmetic'][prefix[index]]
  fresh=sorted(missing(index),key=lambda s:(s not in shared,s))
  order.extend(fresh);gets.update(fresh);introduced=sum(s in shared for s in fresh);births+=introduced
  if introduced:version+=1
  order.append(node);prefix[index]+=1
  if prefix[index]==len(branches[index]['arithmetic']):
   order.append(branches[index]['terminal']);active.remove(index);finished.add(index)
 return order,{'phase_max_open':limit,'phase_shared_roots':len(shared),'phase_shared_births':births,'phase_policy':birth_policy,'phase_branches':len(branches)}

def schedule_root_phases(block,*,time_budget_ms=100,prepared=None):
 if time_budget_ms<=0:raise ValueError('Positive shared-root phase budget required')
 tick=perf_counter();deadline=tick+time_budget_ms/1000;prepared=prepared or PreparedGraph(block,time_budget_ms=time_budget_ms)
 best=None;attempts=[]
 for count,policy in((1,'long_run'),(2,'long_run'),(3,'long_run'),(2,'few_uses')):
  try:
   order,diagnostics=propose_root_phase_order(block,prepared,max_open=count,birth_policy=policy,deadline=deadline)
   candidate=emit_order(block,order,deadline=deadline,cutoff=best['stats']['inserted_copy_count']if best else None)
  except BudgetExceeded:
   if best is None:raise
   attempts.append({'max_open':count,'policy':policy,'outcome':'budget_retained_incumbent'});break
  except InfeasibleSchedule as exc:attempts.append({'max_open':count,'policy':policy,'outcome':str(exc)});continue
  if candidate is None:attempts.append({'max_open':count,'policy':policy,'outcome':'failed_or_no_improvement'});continue
  best=candidate;best['stats'].update(diagnostics);attempts.append({'max_open':count,'policy':policy,'copies':candidate['stats']['inserted_copy_count']})
  if candidate['stats']['inserted_copy_count']==0:break
 if best is None:raise InfeasibleSchedule('No root-phase relay witness; not a general infeasibility proof')
 best['stats'].update(strategy='root_phases',phase_attempts=attempts,elapsed_ms=(perf_counter()-tick)*1000)
 return best
