"""Offline restricted terminal-pair order proposals; no default scheduling change."""
import argparse,json,sys,hashlib
from collections import defaultdict
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.model import parse_block
from isa_scheduler.workloads import generate_workload
from isa_scheduler.local_order import emit_order
from isa_scheduler.pair_copy_bound import pair_copy_bound
from isa_scheduler.consumer_copy_bound import consumer_copy_bound
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify


def orders(block):
    nodes=block.instructions;stores={node.args[0]:node.index for node in nodes if node.op=='SET'};groups=defaultdict(list)
    for node in nodes:
        if node.op in ('ADD','MULW'):groups[tuple(sorted(node.args))].append(node.index)
    for policy in ('pair','block','first_block'):
        order=[];emitted=set()
        for roots,values in sorted(groups.items()):
            order.extend(root for root in roots if root not in emitted);emitted.update(roots)
            tail=min(block.window-1,len(values));prefix=values[:-tail];suffix=values[-tail:]
            chunk=1 if policy=='pair' else block.window-2
            if policy=='first_block' and prefix:
                initial=prefix[:chunk];prefix=prefix[chunk:];order.extend(initial);order.extend(stores[value]for value in initial);chunk=1
            for start in range(0,len(prefix),chunk):
                batch=prefix[start:start+chunk];order.extend(batch);order.extend(stores[value]for value in batch)
            order.extend(suffix);order.extend(stores[value]for value in suffix)
        order.extend(node.index for node in nodes if node.op=='GET' and node.index not in emitted)
        yield policy,order


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--round',default='r79b-terminal-order-evidence');arguments=parser.parse_args()
    folder=ROOT/'experiments'/arguments.round;folder.mkdir(exist_ok=False);records=[];start=perf_counter()
    inputs=(folder/'inputs.jsonl').open('w');outputs=(folder/'optimized_outputs.jsonl').open('w');orders_stream=(folder/'original_orders.jsonl').open('w')
    for size in (32,128,512,2048):
        for bits in (2,3,4,5):
            for sample in range(2):
                seed=4900001+len(records);data=generate_workload(seed,'terminal_root_pairs',size,bits);block=parse_block(data)
                proposed=[candidate for candidate in (consumer_copy_bound(block),pair_copy_bound(block))if candidate]
                input_hash=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                inputs.write(json.dumps({'seed':seed,'input_sha256':input_hash,'input':data})+'\n')
                lower=max(candidate['copy_lower_bound']for candidate in proposed);row={'seed':seed,'input_sha256':input_hash,'nodes':len(block.instructions),'bits':bits,'lower':lower,'candidates':[]}
                for policy,order in orders(block):
                    tick=perf_counter();candidate=emit_order(block,order,deadline=tick+4)
                    if candidate is None:row['candidates'].append({'policy':policy,'status':'fixed_order_failed'});continue
                    verify(data,candidate);check_identity_witness(data,candidate,order)
                    copies=candidate['stats']['inserted_copy_count']
                    core={key:candidate[key]for key in ('block_id','optimized_instructions')}
                    outputs.write(json.dumps({'input_sha256':input_hash,'variant':policy,'output':core})+'\n')
                    orders_stream.write(json.dumps({'input_sha256':input_hash,'variant':policy,'original_order':order})+'\n')
                    if copies<lower:raise ValueError('COPY bound contradicted')
                    row['candidates'].append({'policy':policy,'copies':copies,'optimal_identity_model':copies==lower,'elapsed_ms':(perf_counter()-tick)*1000})
                records.append(row)
    inputs.close();outputs.close();orders_stream.close()
    report={'elapsed_s':perf_counter()-start,'method':'restricted complete disjoint-root terminal groups; original order proposals emitted with generic fixed-order greedy relays; independent symbolic and identity checks',
            'source_manifest':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in (ROOT/'isa_scheduler').glob('*.py')},'records':records}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'elapsed_s':report['elapsed_s'],'graphs':len(records),'exact_graphs':sum(any(candidate.get('optimal_identity_model') for candidate in row['candidates'])for row in records)}))


if __name__=='__main__':main()
