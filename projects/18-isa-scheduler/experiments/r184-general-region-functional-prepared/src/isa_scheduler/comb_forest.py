"""Strict complete comb forests: private GETs adjacent to use, zero COPY.

Each arithmetic node has at most one arithmetic predecessor; every non-SET
identity has one distinct consumer. Pure unique/disjoint architectural names.
Completing each component alone leaves at most the previous result plus two
GETs. Original operand distances are <=2, hence legal for every contest window.
No rewrites, additional GETs, dropped nodes or equivalent-identity substitution.
"""
from time import perf_counter
from .model import BudgetExceeded,InfeasibleSchedule

def recognize_comb_forest(block,*,deadline=float('inf')):
 nodes=block.instructions
 if block.memory_order!='hazard' or any(node.order_deps for node in nodes):return None
 if any(node.op not in ('GET','SET','ADD','MULW')for node in nodes):return None
 reads=[node.reg for node in nodes if node.op=='GET'];writes=[node.reg for node in nodes if node.op=='SET']
 if len(set(reads))!=len(reads)or len(set(writes))!=len(writes)or set(reads)&set(writes):return None
 counts=[0]*len(nodes);previous=[None]*len(nodes)
 for i,node in enumerate(nodes):
  if i%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Comb recognition budget exhausted')
  args=set(node.args)
  if node.op=='SET':previous[i]=node.args[0]
  elif node.op in ('ADD','MULW'):
   internal=[source for source in args if nodes[source].op in ('ADD','MULW')]
   if len(internal)>1 or any(nodes[source].op not in ('GET','ADD','MULW')for source in args):return None
   if internal:previous[i]=internal[0]
  for source in args:counts[source]+=1
 if not any(node.op=='SET'for node in nodes) or any(counts[node.index]!=(0 if node.op=='SET'else 1)for node in nodes):return None
 return previous

def schedule_comb_forest(block,*,time_budget_ms=100,plan=None):
 if time_budget_ms<=0:raise ValueError('Positive comb budget required')
 started=perf_counter();deadline=started+time_budget_ms/1000
 if plan is None:plan=recognize_comb_forest(block,deadline=deadline)
 if plan is None:raise InfeasibleSchedule('comb_forest requires a complete pure single-arithmetic-predecessor forest; no global infeasibility proof')
 nodes=block.instructions;output=[];order=[];positions=[-1]*len(nodes)
 def emit(index):
  if positions[index]>=0:raise ValueError('Comb output attempted to duplicate an original identity')
  node=nodes[index];now=len(output);row={'id':now,'op':node.op}
  if node.reg is not None:row['reg']=node.reg
  if node.args:
   distances=[now-positions[source]for source in node.args]
   if any(positions[source]<0 for source in node.args)or any(not 1<=d<=2 for d in distances):raise ValueError('Comb distance proof failed')
   row['inputs']=[f't#{d}'for d in distances]
  positions[index]=now;output.append(row);order.append(index)
 for sink in nodes:
  if sink.op!='SET':continue
  chain=[];current=sink.index
  while current is not None:
   if len(chain)%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Comb traversal budget exhausted')
   chain.append(current);current=plan[current]
  for index in reversed(chain):
   if len(output)%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Comb emission budget exhausted')
   for source in dict.fromkeys(nodes[index].args):
    if nodes[source].op=='GET' and positions[source]<0:emit(source)
   emit(index)
 if len(order)!=len(nodes):raise ValueError('Comb plan did not cover every original identity')
 return {'block_id':block.block_id,'optimized_instructions':output,'stats':{
  'strategy':'comb_forest','original_instruction_count':len(nodes),'optimized_instruction_count':len(output),
  'inserted_copy_count':0,'total_copy_count':0,'copy_ratio_output':0.0,'inserted_copy_ratio_original':0.0,
  'original_order':order,'bit_width':block.bit_width,'max_back_distance':block.window,
  'elapsed_ms':(perf_counter()-started)*1000,'comb_scope':'complete pure original-once forest; at most one arithmetic predecessor; all references <=2'}}
