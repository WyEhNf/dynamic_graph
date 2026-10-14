"""Exact live-set/edge/CPU-time validation of actual bounded-search orders."""
import hashlib,json
from pathlib import Path
def main():
    p=Path('reports/projection-search-orders-batch47.json');rows=json.loads(p.read_text())['cases'];inputs={x['name']:x for x in json.loads(Path('data/projection-gold-batch45.json').read_text())['cases']};checks=[]
    for row in rows:
        c=inputs[row['name']];nodes={v['id']:v for v in c['nodes']};children={i:set() for i in nodes}
        for i,v in nodes.items():
            for parent in v['inputs']:children[parent].add(i)
        order=row['order'];assert len(order)==len(set(order))==len(nodes) and set(order)==nodes.keys()
        done=set();peak=0
        for i in order:
            v=nodes[i];assert set(v['inputs'])<=done
            live=sum(nodes[p]['output_memory'] for p in done if not children[p] or children[p]-done)
            current=live+v['workspace_memory']+v['output_memory'];peak=max(peak,current)
            assert current<=c['hardware']['memory_limit'];assert 1<=v['core_num']<=c['hardware']['aic_core_num' if v['core_type']=='AIC' else 'aiv_core_num'];done.add(i)
        time=sum(v['exec_time'] for v in nodes.values());assert time<=c['deadline_us'] and time<=2**63-1
        checks.append(dict(name=row['name'],T=time,peak=peak))
    report=dict(status='passed',orders=len(rows),input_sha=hashlib.sha256(Path('data/projection-gold-batch45.json').read_bytes()).hexdigest(),raw_orders_sha=hashlib.sha256(p.read_bytes()).hexdigest(),reference='Independent Python prefix/future live-set bigint, edge ordering, all original nodes exactly once, both core pools and serial zero-event deadline',cases=checks)
    Path('reports/projection-search-bigint-batch47.json').write_text(json.dumps(report,indent=2));print(len(rows),'actual bounded-search orders independently passed')
if __name__=='__main__':main()
