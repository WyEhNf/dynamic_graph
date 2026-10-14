"""Root raw-set cut recomputation and complete bigint fixed-plan replay."""
import json
import subprocess
import time
from pathlib import Path
from review_stage2_functional_plans_r44 import simulate, sha

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'projects/27-aicore-streams'


def cut(case):
    nodes = {n['id']: n for n in case['nodes']}
    children = {i: set() for i in nodes}
    for i, node in nodes.items():
        assert len(node['inputs']) == len(set(node['inputs']))
        for p in node['inputs']:
            children[p].add(i)
    done = set(); cap = case['hardware']['memory_limit']
    def live():
        return sum(n['output_memory'] for i, n in nodes.items() if i in done and (not children[i] or children[i]-done))
    for i in case['prefix']:
        assert i not in done and set(nodes[i]['inputs']) <= done
        assert live()+nodes[i]['workspace_memory']+nodes[i]['output_memory'] <= cap
        done.add(i)
    initial = peak = live(); order = []; closure = set(); producer = case['producer']
    if producer not in done or not nodes[producer]['output_memory'] or not children[producer]-done:
        return False, closure, order, initial, peak, initial
    pending = list(children[producer]-done)
    while pending:
        i = pending.pop()
        if i in done or i in closure:
            continue
        closure.add(i)
        pending.extend(nodes[i]['inputs'])
    if len(closure) > 128:
        return False, set(), order, initial, peak, initial
    while closure-done:
        ready = []
        for i in closure-done:
            node = nodes[i]
            if not set(node['inputs']) <= done:
                continue
            allocation = live()+node['workspace_memory']+node['output_memory']
            if allocation > cap:
                continue
            before, completed = live(), done | {i}
            held_after = sum(n['output_memory'] for p, n in nodes.items()
                             if p in completed and (not children[p] or children[p]-completed))
            ready.append(((held_after-before, node['workspace_memory']+node['output_memory'], i), i, allocation))
        if not ready:
            return False, closure, order, initial, peak, initial
        _, i, allocation = min(ready)
        peak = max(peak, allocation); done.add(i); order.append(i)
    assert not children[producer]-done
    return True, closure, order, initial, peak, live()


def main():
    paths = [P/'data/release-cut-gold-batch51.json', P/'data/release-cut-fixed-gold-batch51.json',
             P/'research/batch51/release-cut-full-plans.json']
    cases, fixed, full = [json.loads(p.read_text())['cases'] for p in paths]
    assert len(cases) == len(fixed) == len(full) == 102
    by_fixed = {c['name']: c for c in fixed}; by_full = {c['name']: c for c in full}
    valid_cuts = valid_plans = 0; invalid = []
    for case in cases:
        valid, closure, order, initial, peak, final = cut(case); gold = case['gold']
        assert valid == gold['valid'] and closure == set(gold['pending']) and order == gold['order']
        assert (initial, peak, final if valid else initial) == tuple(int(gold[k]) for k in ('initial_live', 'peak', 'final_live'))
        valid_cuts += valid
        f = by_fixed[case['name']]; actual = by_full[case['name']]
        assert actual['original_input'] == {k: case[k] for k in ('nodes', 'hardware', 'deadline_us')}
        assert f['fixed_plan'] == actual['plan']
        # A wider artificial capacity computes the exact peak even for the two
        # expected-invalid schedules; no int64 saturation is used in this gold.
        wide = dict(actual['original_input'], hardware=dict(case['hardware']))
        wide['hardware']['memory_limit'] = sum(n['output_memory']+n['workspace_memory'] for n in case['nodes'])
        T, peak = simulate(wide, actual['plan'])
        valid = peak <= case['hardware']['memory_limit']
        assert (T, peak, valid) == (int(f['gold_T']), int(f['gold_peak']), f['gold_valid'])
        if valid:
            assert simulate(actual['original_input'], actual['plan']) == (T, peak)
            valid_plans += 1
        else:
            invalid.append(case['name'])
    assert (valid_cuts, valid_plans) == (73, 100)
    exe = P/'research/batch51/test_release_cut.exe'
    assert sha(exe) == '73a43350a0c812f81cab7255bbca52a1c6dca3bf652906208cbb460ee94e0c96'
    proc = subprocess.run([str(exe), str(paths[0])], capture_output=True, text=True)
    assert proc.returncode == 0 and proc.stdout.strip() == '102 original remaining-DIRECT/ancestor cut bigint controls passed' and not proc.stderr
    result = dict(passed=True, reviewed_unix=time.time(), independent_cut_controls=102, valid_cuts=73,
                  independent_full_plans=102, feasible_full_plans=100, expected_invalid_full_plans=invalid,
                  root_executable_actual_exit_code=proc.returncode, root_executable_stdout=proc.stdout,
                  evidence={p.relative_to(ROOT).as_posix(): sha(p) for p in paths+[exe]},
                  scope='Raw original-ancestor closure and full live-output sets independently recomputed. All102 full original plans replayed in bigint heap model, including above-int64 expected-invalid allocation. Direct external users/sinks retained, cutoff128/129 tested. Frozen diagnostic component rerun by root; separate Release/UBSan acceptance remains pending.')
    (ROOT/'outputs/stage2-root-release-cut-gold-r51.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
