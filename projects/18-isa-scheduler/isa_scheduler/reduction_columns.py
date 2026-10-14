"""Original-once column orders for shared-input multiply/reduction forests.

No ADD reassociation, product deletion, duplicated GET, or value aliasing.
Every reduction's original ordered binary tree is retained. Only scheduling
of independent rows/columns changes, with physical COPY relays as required.
"""
from time import perf_counter
from .closed_subgraph import projection_eligible
from .local_order import emit_order
from .model import BudgetExceeded,InfeasibleSchedule

def recognize_reduction_columns(block,*,deadline=float('inf')):
 if not projection_eligible(block):return None
 nodes=block.instructions;n=len(nodes);users=[[]for _ in nodes]
 for node in nodes:
  if node.index%128==0 and perf_counter()>=deadline:raise BudgetExceeded('Reduction-column recognition budget exhausted')
  for source in set(node.args):users[source].append(node.index)
 stores=[node.index for node in nodes if node.op=='SET']
 if not 2<=len(stores)<=32 or len(stores)+2>block.window:return None
 covered=set();rows=[];reference=None
 for terminal in stores:
  current=nodes[terminal].args[0];tail=[];seen=set()
  while nodes[current].op=='ADD':
   if current in seen:return None
   seen.add(current);node=nodes[current]
   if len(node.args)!=2 or len(set(node.args))!=2:return None
   a,b=node.args;ops=(nodes[a].op,nodes[b].op)
   if ops==('MULW','MULW'):
    products=[a,b];additions=[None,current];break
   if ops not in (('ADD','MULW'),('MULW','ADD')):return None
   previous,product=(a,b)if ops[0]=='ADD'else(b,a)
   tail.append((product,current));current=previous
  else:return None
  for product,addition in reversed(tail):products.append(product);additions.append(addition)
  if len(set(products))!=len(products):return None
  weights=[];private=[]
  for product in products:
   source=nodes[product]
   if len(source.args)!=2 or len(set(source.args))!=2 or any(nodes[i].op!='GET'for i in source.args):return None
   shared=[i for i in source.args if len(users[i])==len(stores)]
   isolated=[i for i in source.args if len(users[i])==1]
   if len(shared)!=1 or len(isolated)!=1 or len(users[product])!=1:return None
   weights.append(shared[0]);private.append(isolated[0])
  if len(set(weights))!=len(weights)or len(set(private))!=len(private):return None
  if reference is None:reference=weights
  elif reference!=weights:return None
  own={terminal,*products,*private,*(i for i in additions if i is not None)}
  if covered&own or any(len(users[i])!=1 for i in additions if i is not None):return None
  covered.update(own);rows.append({'terminal':terminal,'products':products,'private':private,'additions':additions})
 covered.update(reference)
 if covered!=set(range(n)):return None
 return {'rows':rows,'weights':reference,'width':len(reference),'original_nodes':n,
         'scope':'complete disjoint original ADD/MULW reduction trees with common weight GET identities; no rewrites'}

def schedule_reduction_columns(block,*,time_budget_ms=100,plan=None):
 if time_budget_ms<=0:raise ValueError('Positive column-order budget required')
 tick=perf_counter();deadline=tick+time_budget_ms/1000;plan=plan or recognize_reduction_columns(block,deadline=deadline)
 if plan is None:raise InfeasibleSchedule('Reduction-column strict structure not matched; no global proof')
 count=len(plan['rows']);best=None;attempts=[]
 for policy,batch_size in(('forward',1),('forward',2),('forward',count),('reverse',1),('reverse',2),('alternating',1),('alternating',2)):
  order=[]
  try:
   for column,weight in enumerate(plan['weights']):
    if column%32==0 and perf_counter()>=deadline:raise BudgetExceeded('Reduction-column order budget exhausted')
    order.append(weight);indices=list(range(count))
    if policy=='reverse'or policy=='alternating'and column%2:indices.reverse()
    for offset in range(0,count,batch_size):
     group=indices[offset:offset+batch_size]
     for index in group:
      row=plan['rows'][index];order.extend((row['private'][column],row['products'][column]))
     for index in group:
      row=plan['rows'][index];addition=row['additions'][column]
      if addition is not None:order.append(addition)
      if column==plan['width']-1:order.append(row['terminal'])
   candidate=emit_order(block,order,deadline=deadline,cutoff=best['stats']['inserted_copy_count']if best else None)
  except BudgetExceeded:
   if best is None:raise
   attempts.append({'policy':policy,'batch_size':batch_size,'outcome':'budget_retained_incumbent'});break
  if candidate is None:attempts.append({'policy':policy,'outcome':'failed_or_no_improvement'});continue
  copies=candidate['stats']['inserted_copy_count'];attempts.append({'policy':policy,'batch_size':batch_size,'copies':copies})
  best=candidate;best['stats'].update(column_order_policy=policy,column_product_batch=batch_size)
  if copies==0:break
 if best is None:raise InfeasibleSchedule('Column relay orders did not produce a witness; no global proof')
 best['stats'].update(strategy='reduction_columns',elapsed_ms=(perf_counter()-tick)*1000,
                      reduction_rows=count,reduction_width=plan['width'],column_order_attempts=attempts,
                      scope=plan['scope'])
 return best
