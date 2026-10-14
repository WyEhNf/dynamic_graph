"""Offline contraction minimum-degree lower-bound probe, not default solver."""
import json,sys,hashlib
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.model import parse_block
from isa_scheduler.workloads import generate_workload


def minor_bound(block,budget_ms=1000):
    started=perf_counter();deadline=started+budget_ms/1000
    adj={node.index:set(node.args) for node in block.instructions}
    for index,args in list(adj.items()):
        for source in args:adj[source].add(index)
    bound=0;actions=[];outcome='complete'
    while adj:
        if perf_counter()>=deadline:outcome='time_budget_exhausted';break
        vertex=min(adj,key=lambda index:(len(adj[index]),index));degree=len(adj[vertex]);bound=max(bound,degree)
        if bound>block.window:outcome='infeasible_under_identity_model';break
        if not degree:actions.append(('delete',vertex));del adj[vertex];continue
        target=min(adj[vertex],key=lambda index:(len(adj[index]),index))
        neighbors=adj[vertex]-{target};adj[target].update(neighbors);adj[target].discard(vertex)
        for neighbor in neighbors:adj[neighbor].discard(vertex);adj[neighbor].add(target)
        actions.append(('contract',vertex,target));del adj[vertex]
    return {'lower_bound':bound,'window':block.window,'outcome':outcome,'actions':actions,
            'elapsed_ms':(perf_counter()-started)*1000,'remaining_vertices':len(adj)}


if __name__=='__main__':
    records=[]
    for family in ('matrix_product_tile','dot_product_many','sparse_shared','cross_group_shared'):
        for size in (64,256,1024,4096):
            for bits in (2,3,4,5):
                data=generate_workload(3300001,family,size,bits);row=minor_bound(parse_block(data))
                row.update(family=family,target_nodes=size,nodes=len(data['instructions']),bit_width=bits,
                           input_sha256=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest())
                records.append(row)
                print(json.dumps({k:v for k,v in row.items() if k!='actions'}),flush=True)
    path=ROOT/'experiments/r58-minor-probe.json';path.write_text(json.dumps({'records':records},indent=2)+'\n')
