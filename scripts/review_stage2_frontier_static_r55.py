"""Independently check saved-state one-step and necessary-overlap negatives."""
from pathlib import Path
import hashlib
import json
import time

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/27-aicore-streams'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    frontier = read(P/'research/batch55/saved-frontier-static.json')
    mandatory = read(P/'research/batch55/saved-mandatory-frontier-static.json')
    for source in frontier['input_sources'] + mandatory['sources']:
        path = Path(source['path'])
        assert sha(path if path.is_absolute() else P/path) == source['sha256']
    cases = {c['name']:c for c in read(P/'research/batch52/observer-selected12-input-only.json')['cases']}
    observer = {c['name']:c for c in read(P/'reports/observer-observed-batch52.json')['cases']}
    found = {(r['name'],r['saved_snapshot_index']):r for r in frontier['rows']}
    overlap = {(r['name'],r['saved_snapshot_index']):r for r in mandatory['rows']}
    assert len(found) == len(overlap) == 22 and found.keys() == overlap.keys()
    preserving = early = early_failed = 0
    for (name,index),row in found.items():
        graph = {v['id']:v for v in cases[name]['nodes']}; children = {i:set() for i in graph}
        for v in graph.values():
            for p in v['inputs']: children[p].add(v['id'])
        cap = cases[name]['hardware']['memory_limit']
        snap = observer[name]['helper_observer']['snapshots'][index]
        assert snap['kind']=='probe' and snap['reason']=='ready_but_no_fit' and not snap['transition_may_be_incomplete']
        D = {i for i,done in zip(snap['node_ids'],snap['done']) if done}; C = set(snap['closure_construction_seen_ids'])
        def live(done): return sum(graph[p]['output_memory'] for p in done if not children[p] or children[p]-done)
        def choices(done): return {i for i in C-done if set(graph[i]['inputs']) <= done and live(done)+graph[i]['workspace_memory']+graph[i]['output_memory'] <= cap}
        last = snap['probe_completed_order'][-1]; before = D-{last}
        assert live(D)==snap['live'] and not choices(D) and last in choices(before)
        assert sorted(choices(before)) == row['initial_available_ids']
        alternatives = {i for i in choices(before)-{last} if choices(before|{i})}
        assert alternatives == {a['id'] for a in row['preserving_other_candidates']}
        preserving += bool(alternatives)
        # Independently find descendants by DFS; include all original direct
        # parents once and only completed outputs necessarily live at j BEGIN.
        reach = {}
        for j in C:
            visited = set(); stack = [j]
            while stack:
                v = stack.pop()
                if v in visited: continue
                visited.add(v); stack.extend(children[v]&C)
            reach[j] = visited
        def bad(done):
            result = {}
            for j in C-done:
                parents = set(graph[j]['inputs'])
                held = parents | {p for p in done if not children[p] or children[p]&reach[j]}
                value = graph[j]['workspace_memory']+graph[j]['output_memory']+sum(graph[p]['output_memory'] for p in held)
                if value > cap: result[j] = value
            return result
        current = D-set(snap['probe_completed_order']); first = None
        assert not bad(current)
        for step,chosen in enumerate(snap['probe_completed_order']):
            assert chosen in choices(current)
            violation = bad(current|{chosen})
            if violation:
                alternative = {i for i in choices(current)-{chosen} if not bad(current|{i})}
                first = (step,chosen,violation,alternative); break
            current.add(chosen)
        reported = overlap[name,index]['first_irreversible_original_transition']
        assert (first is None) == (reported is None)
        if first:
            step,chosen,violation,alternatives = first
            assert (step,chosen) == (reported['probe_step'],reported['original_choice'])
            assert violation == {v['id']:v['necessary_overlap'] for v in reported['bad_future_targets']}
            assert alternatives == {v['id'] for v in reported['preserving_alternatives']}
            early += 1; early_failed += not observer[name]['whole']['valid']
    assert preserving == 0 and early == 2 and early_failed == 0
    result = dict(passed=True,reviewed_unix=time.time(),saved_no_fit_states=22,last_step_preserving_alternatives=0,
        necessary_overlap_first_irreversible_states=2,failed_case_early_alternatives=0,
        source_reports_sha256=[sha(P/'research/batch55'/name) for name in ('saved-frontier-static.json','saved-mandatory-frontier-static.json')],
        scope='Root independent original-direct-edge/set arithmetic and DFS matches saved22 snapshots. One-step substitution has no next-fit alternative here; two necessary-overlap transitions occur only in already-recovered controls. Snapshot subset does not rule out earlier/deeper choices or all63 recovery. No solver/new graph/search/default/performance execution.')
    (ROOT/'outputs/stage2-root-frontier-static-r55.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': main()
