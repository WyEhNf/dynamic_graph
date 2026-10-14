"""Necessary COPY lower bound for complete shared multiply/reduction rows.

Track the R current row accumulator roles, retaining exact original identities.
An original ADD refreshes one role, COPY may refresh one; no nodes are merged.
See research/level-stage/shared-reduction-proof.md for interval/edge accounting.
"""
from .reduction_columns import recognize_reduction_columns
from .raw_pure import dependencies
from .persistent_cut_bound import _pure_names
from .model import InvalidBlock

def _lower(rows,width,window):
 slack=window-rows;g=max(0,(2*rows+1)*width-(4*rows+2)*window)
 return max(0,(rows*g+slack-1)//slack-rows*(width-1)-rows),g

def reduction_copy_bound(block):
 plan=recognize_reduction_columns(block)
 if plan is None or plan['width']<=block.window:return None
 count=len(plan['rows']);lower,g=_lower(count,plan['width'],block.window)
 if not lower:return None
 return {'kind':'shared_reduction_accumulator_age_sum','window':block.window,'copy_lower_bound':lower,
         'witness':{'weights':plan['weights'],'rows':plan['rows'],'forced_nonrefresh_originals':g},
         'scope':'all original-once orders; complete original ADD chains; distinct GET/MULW/ADD identities; COPY-only; no aliases/recompute/reread/spill/reassociation'}

def check_reduction_copy_certificate(data,certificate):
 args=dependencies(data);instructions=data['instructions'];n=len(args);w=2**data['bit_width'];proof=certificate.get('witness');claim=certificate.get('copy_lower_bound')
 if not _pure_names(instructions)or certificate.get('kind')!='shared_reduction_accumulator_age_sum'or certificate.get('window')!=w or type(claim)is not int or claim<0 or not isinstance(proof,dict):raise InvalidBlock('Invalid shared-reduction certificate')
 weights=proof.get('weights');rows=proof.get('rows')
 if not isinstance(weights,list)or not isinstance(rows,list)or not 2<=len(rows)<w or len(weights)<=w:raise InvalidBlock('Shared reduction dimensions outside proof scope')
 def indices(values):
  if not isinstance(values,list)or any(type(i)is not int or not 0<=i<n for i in values)or len(set(values))!=len(values):raise InvalidBlock('Invalid/duplicate reduction-role indices')
 indices(weights)
 if any(instructions[i]['op']!='GET'for i in weights):raise InvalidBlock('Weights must be GET identities')
 covered=set(weights);m=len(weights)
 for row in rows:
  if not isinstance(row,dict):raise InvalidBlock('Invalid reduction row')
  private=row.get('private');products=row.get('products');adds=row.get('additions');terminal=row.get('terminal')
  indices(private);indices(products)
  if len(private)!=m or len(products)!=m or not isinstance(adds,list)or len(adds)!=m or adds[0]is not None or type(terminal)is not int or not 0<=terminal<n:raise InvalidBlock('Invalid reduction-chain lengths')
  indices(adds[1:]);own=set(private+products+adds[1:]+[terminal])
  if len(own)!=3*m or covered&own:raise InvalidBlock('Reduction rows must have disjoint original identities')
  for j,(x,product)in enumerate(zip(private,products)):
   if instructions[x]['op']!='GET'or instructions[product]['op']!='MULW'or len(args[product])!=2 or set(args[product])!={weights[j],x}:raise InvalidBlock('Original product is not weight/private MULW')
   if j:
    previous=products[0]if j==1 else adds[j-1]
    if instructions[adds[j]]['op']!='ADD'or len(args[adds[j]])!=2 or set(args[adds[j]])!={previous,product}:raise InvalidBlock('Original ADD chain does not match roles')
  if instructions[terminal]['op']!='SET'or args[terminal]!=(adds[-1],):raise InvalidBlock('Original SET does not consume final sum')
  covered.update(own)
 if covered!=set(range(n)):raise InvalidBlock('Reduction certificate must cover every original node')
 lower,g=_lower(len(rows),m,w)
 if proof.get('forced_nonrefresh_originals')!=g or claim>lower:raise InvalidBlock('Shared-reduction age inequality not established')
 return {'verified_global_copy_lower_bound':lower,'scope':'all topological original-once COPY-only orders of the complete checked shared-reduction graph'}
