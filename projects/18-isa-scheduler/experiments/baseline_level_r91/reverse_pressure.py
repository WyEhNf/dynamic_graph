"""Bottom-up dynamic liveness order proposals, then legal expiry relays.

Inspired by Chen's min-reg RP-reduction/shared-use heuristics (arXiv2303.06855),
not an implementation of its CP-SAT or O(n^2) full clustering algorithm.
All original nodes and ordered arguments remain; memory order edges included.
Peak reverse pressure is only a heuristic metric, NOT a distance feasibility or
COPY optimality proof. Unknown feasibility and budget exhaustion are distinct.
"""
import heapq
from time import perf_counter
from .incremental import PreparedGraph
from .local_order import emit_order
from .model import BudgetExceeded,InfeasibleSchedule

def propose_order(block,*,policy='reverse_pressure',deadline=float('inf'),prepared=None):
 if policy not in ('reverse_pressure','reverse_cluster','reverse_span'):raise ValueError('Unknown reverse policy')
 graph=prepared or PreparedGraph(block,time_budget_ms=max(0,(deadline-perf_counter())*1000)if deadline!=float('inf')else None)
 if graph.block is not block:raise ValueError('Prepared graph belongs to another block')
 n=len(block.instructions);pending=[len(users)for users in graph.users];need=[1]*n
 for i,args in enumerate(graph.args_unique):
  if i%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Reverse demand preparation budget exhausted')
  need[i]=max((weight+offset for offset,weight in enumerate(sorted((need[s]for s in args),reverse=True))),default=1)
 unlock_counts=[sum(pending[s]==1 for s in graph.deps[i])for i in range(n)]
 ready=set(i for i,count in enumerate(pending)if not count);versions=[0]*n;live=set();birth=[n+1]*n;heap=[];reverse=[];peak=0;pushes=0
 def key(i):
  args=graph.args_unique[i];delta=sum(s not in live for s in args)-int(i in live)
  unlock=unlock_counts[i];age=birth[i] if i in live else n+1
  if policy=='reverse_cluster':return delta,-unlock,need[i],age,-i
  if policy=='reverse_span':return delta,age,-unlock,need[i],-i
  return delta,need[i],age,-unlock,-i
 def push(i):
  nonlocal pushes
  versions[i]+=1;heapq.heappush(heap,(key(i),i,versions[i]));pushes+=1
 for i in ready:push(i)
 operations=0
 while len(reverse)<n:
  operations+=1
  if operations%128==1 and perf_counter()>=deadline:raise BudgetExceeded('Reverse ordering budget exhausted')
  while heap:
   _,i,version=heapq.heappop(heap)
   if i in ready and version==versions[i]:break
  else:raise InfeasibleSchedule('Reverse proposal has no ready node; no global proof')
  ready.remove(i);reverse.append(i);affected=set()
  if i in live:
   live.remove(i);affected.update(graph.data_users[i])
  for s in graph.args_unique[i]:
   if s not in live:
    live.add(s);birth[s]=len(reverse);affected.add(s);affected.update(graph.data_users[s])
  peak=max(peak,len(live))
  for s in graph.deps[i]:
   pending[s]-=1
   # A candidate's local unlock score changes only when pending crosses one.
   # Notify all users on that boundary, avoiding quadratic fanout rescans.
   if pending[s]<=1:
    adjustment=1 if pending[s]==1 else -1
    for user in graph.users[s]:unlock_counts[user]+=adjustment
    affected.update(graph.users[s])
   if pending[s]==0:ready.add(s);affected.add(s)
  for candidate in affected&ready:push(candidate)
 return list(reversed(reverse)),{'reverse_peak_live':peak,'reverse_heap_pushes':pushes,'reverse_heap_pops':operations,'scope':'heuristic pressure only; every original node once and original ordered dependencies retained'}

def schedule_reverse_pressure(block,*,policy='reverse_pressure',time_budget_ms=100,prepared=None):
 if time_budget_ms<=0:raise ValueError('Positive reverse time budget required')
 started=perf_counter();deadline=started+time_budget_ms/1000
 order,diagnostics=propose_order(block,policy=policy,deadline=deadline,prepared=prepared);order_ms=(perf_counter()-started)*1000
 result=emit_order(block,order,deadline=deadline)
 if result is None:raise InfeasibleSchedule('Reverse fixed-order relay failed; no global infeasibility claim')
 result['stats'].update(diagnostics,strategy=policy,reverse_order_ms=order_ms,elapsed_ms=(perf_counter()-started)*1000)
 return result
