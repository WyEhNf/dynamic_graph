"""Independent bigint full original-DAG serial orders; no candidate invocation."""
import itertools
import json
import time
from review_stage2_frontier_static_r55 import ROOT, P, sha, read

def main():
    d = P/'research/batch55'
    controls = read(d/'manual-original-orders.json')['controls']
    physics = read(d/'manual-original-physics.json')
    for row in physics['sources']:
        from pathlib import Path
        path = Path(row['path']); assert sha(path if path.is_absolute() else P/path) == row['sha256']
    actual = {r['name']:r for r in physics['results']}; results = []; all_orders = 0
    for control in controls:
        case = control['case']; nodes = {v['id']:v for v in case['nodes']}; users = {i:set() for i in nodes}
        for v in nodes.values():
            for p in v['inputs']: users[p].add(v['id'])
        cap = case['hardware']['memory_limit']
        def held(D): return {p for p in D if not users[p] or users[p]-D}
        def live(D): return sum(nodes[p]['output_memory'] for p in held(D))
        def replay(order):
            D = set(); t = peak = 0; rows = []
            for i in order:
                if i in D or not set(nodes[i]['inputs']) <= D: return None
                overlap = live(D)+nodes[i]['workspace_memory']+nodes[i]['output_memory']
                peak = max(peak,overlap)
                if overlap > cap:
                    rows.append(dict(id=i,begin_time=t,live_before=live(D),workspace=nodes[i]['workspace_memory'],new_output=nodes[i]['output_memory'],compute_overlap=overlap))
                    return dict(valid=False,peak=peak,T=None,complete=False,rows=rows)
                begin = t; before = live(D); previous = held(D)
                t += nodes[i]['exec_time']; D.add(i)
                rows.append(dict(id=i,begin_time=begin,live_before=before,workspace=nodes[i]['workspace_memory'],
                    new_output=nodes[i]['output_memory'],compute_overlap=overlap,end_time=t,
                    released_original_direct_parent_outputs=sorted(previous-held(D)),live_after=live(D),held_output_ids=sorted(held(D))))
            return dict(valid=len(D)==len(nodes) and t<=case['deadline_us'],peak=peak,T=t,complete=len(D)==len(nodes),rows=rows)
        current = replay(control['supplied_full_order']); stored = actual[case['name']]
        assert current is not None and current['valid'] == control['expected_valid'] == stored['valid']
        for key in ('peak','T','complete','rows'): assert current[key] == stored[key], (case['name'],key)
        legal_orders = 0; minimum_peak = None; prefix_classes = {}
        for permutation in itertools.permutations(nodes):
            D = set(); topological = True
            for i in permutation:
                if not set(nodes[i]['inputs'])<=D: topological=False; break
                D.add(i)
            if not topological: continue
            all_orders += 1; value = replay(permutation)
            if value['valid']:
                legal_orders += 1; minimum_peak = value['peak'] if minimum_peak is None else min(minimum_peak,value['peak'])
                prefix_classes[permutation[:2]] = prefix_classes.get(permutation[:2],0)+1
        if case['name']=='equal-live-distinct-identity-correct':
            assert live({0,1}) == live({0,2}) == 70
            assert prefix_classes.get((0,1),0)==0 and prefix_classes.get((0,2),0)>0
        results.append(dict(name=case['name'],supplied_valid=current['valid'],supplied_peak=current['peak'],
                            legal_serial_orders=legal_orders,minimum_legal_serial_peak=minimum_peak))
    assert len(controls)==8 and sum(r['supplied_valid'] for r in results)==5
    result = dict(passed=True,reviewed_unix=time.time(),manual_controls=8,legal_supplied_orders=5,expected_invalid_supplied_orders=3,
        original_topological_orders_enumerated=all_orders,controls=results,
        manual_inputs_sha256=sha(d/'manual-original-orders.json'),manual_physics_sha256=sha(d/'manual-original-physics.json'),
        scope='Root independently enumerated original topological serial orders with bigint BEGIN W+O and last originalDIRECT END release/sink retention. Equal-live70 distinct completed identities have different continuation feasibility. FullDAG manual counterexamples support branching within failed cut, not actual failed63 recovery or production wholedefault failure.')
    (ROOT/'outputs/stage2-root-frontier-manual-r55.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
