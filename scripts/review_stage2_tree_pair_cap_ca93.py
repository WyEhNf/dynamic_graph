"""Root full-output and independent original physical-prefix audit for R176."""
from collections import Counter
import difflib
import json
import subprocess
import time
from review_stage2_tree_pair_serial_controls import ROOT, P, replay, fingerprint, distance, sha
from review_stage2_tree_anytime_diagnostics import physical_prefix

def read(path): return json.loads(path.read_text(encoding='utf-8'))

def audit_frontier(data, baseline, stats, path):
    args = [[i-distance(t) for t in row.get('inputs', [])] for i,row in enumerate(data['instructions'])]
    users = [set() for _ in args]
    for v, operands in enumerate(args):
        for p in operands: users[p].add(v)
    start = stats['rank_interval'][0]; sides = stats['sides']
    D = set(baseline['original_order'][:start]); window = 1 << data['bit_width']
    labels = {}; physical = {}; counts = Counter(); completed_cache = {}
    item = dict(input=data, baseline=baseline, stats=stats)
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            rec = json.loads(line); counts[rec['kind']] += 1
            if rec['kind'] == 'frontier_header':
                assert rec['actual_open_count'] == stats['actual_open_count']; continue
            if rec['kind'] == 'immutable_path_label':
                version = rec['label_version']; predecessor = rec['predecessor_label']; action = rec['action']
                if predecessor is None:
                    offsets,g,roles,ages = physical_prefix(item, [])
                    last = {v:g-age for v,age in zip(roles,ages)}
                else:
                    assert predecessor < version
                    offsets = list(labels[predecessor]['prefixes'])
                    g,last = physical[predecessor]; last = dict(last)
                if action is not None:
                    side,offset = action; assert offset == offsets[side]
                    v = sides[side][offset]; offsets[side] += 1
                    operands = set(args[v]); assert operands <= set(last)
                    rotates = 0
                    while last:
                        p = min(last, key=last.get); age = g-last[p]
                        if age < window or p in operands: break
                        assert age == window and rotates < window
                        last[p] = g; g += 1; rotates += 1
                    assert all(1 <= g-last[p] <= window for p in operands)
                    g += 1; pair = tuple(offsets)
                    if pair not in completed_cache:
                        completed_cache[pair] = D | set(sides[0][:offsets[0]]) | set(sides[1][:offsets[1]])
                    completed = completed_cache[pair]
                    for p in operands:
                        if not users[p]-completed: del last[p]
                    if users[v]-completed: last[v] = g-1
                roles = stats['external_roles'] + sorted(set(last)-set(stats['external_roles']))
                assert offsets == rec['prefixes'] and g == rec['g']
                assert [g-last[v] for v in roles] == rec['ages']
                assert rec['h'] == len(args)-start-sum(offsets)
                labels[version] = rec; physical[version] = (g,last)
            else:
                assert rec['kind'] in ('open','unfinished_expansion')
                label = labels[rec['label_version']]; g,last = physical[rec['label_version']]
                roles = stats['external_roles'] + sorted(set(last)-set(stats['external_roles']))
                assert [rec['i'],rec['j']] == label['prefixes']
                assert rec['g'] == g and rec['h'] == label['h']
                assert rec['roles'] == roles and rec['ages'] == [g-last[v] for v in roles]
    assert counts['open'] == stats['actual_open_count']
    assert bool(counts['unfinished_expansion']) == (stats['unfinished_expansion'] is not None)
    return counts

def main():
    d = P / 'experiments/r176-anytime-wrapper-cap-ca93'
    for name,digest in read(d/'source-provenance.json')['source_sha256'].items(): assert sha(d/'src'/name) == digest
    for name,digest in read(d/'evidence-provenance.json')['evidence_sha256'].items(): assert sha(P/name) == digest
    old = (P/'experiments/r172-tree-pair-anytime-84/src/isa_scheduler/tree_pair_anytime_refine.py').read_text()
    new = (d/'src/isa_scheduler/tree_pair_anytime_refine.py').read_text()
    diff = list(difflib.unified_diff(old.splitlines(True),new.splitlines(True)))
    assert sum(s.startswith('@@') for s in diff) == 3
    start = '        block=parse_block'; end = '        for parent,child_copies'
    assert old[old.index(start):old.index(end)] == new[new.index(start):new.index(end)]
    assert sha(d/'src/isa_scheduler/tree_pair_anytime.py') == 'dac3b71701e4085f7fb7e1ca2f829937cbb028cc8b68a773c1021ff16c1477c7'
    data = read(d/'input.json'); baseline = read(d/'baseline-output.json'); report = read(d/'report.json')
    assert fingerprint(data) == report['input_sha256']
    full = 0
    def check(candidate):
        nonlocal full
        cost = replay(data,dict(candidate,input_sha256=fingerprint(data))); full += 1
        if 'copies' in candidate: assert cost == candidate['copies']
        return cost
    assert check(baseline) == 23
    assert check(read(d/'best-output.json')) == 22
    assert check(read(d/'historical-dp21-only-comparison.json')) == 21
    proposals = sorted(d.glob('parent*-candidate*-output.json'))
    assert len(proposals) == report['actual_complete_proposals'] == 119
    costs = [check(read(p)) for p in proposals]
    assert min(costs) == 22
    synthetic = read(d/'synthetic-control-report.json')
    assert synthetic['tests_run'] == 6 and not synthetic['failures'] and not synthetic['errors']
    synthetic_paths = sorted(d.glob('synthetic-*-output.json'))
    assert len(synthetic_paths) == synthetic['physical_sink_outputs'] == 98
    for path in synthetic_paths:
        row = read(path); assert row['synthetic_child'] and row['input'] == data
        check(row['candidate'])
    stats = report['stats']; attempts = stats['attempts']; counts = Counter()
    assert len(attempts) == len(stats['eligible_parents']) == 19
    assert [r['parent'] for r in attempts] == [r[0] for r in stats['eligible_parents']]
    assert stats['processed_states'] == sum(r['processed_states'] for r in attempts) == 10722
    assert stats['complete_outputs'] == sum(r['complete_outputs'] for r in attempts) == 119
    assert stats['outcome'] == 'partial_outlet_limit' and stats['outlet_limited_parents'] == [61,59]
    for attempt in attempts:
        child = attempt['stats']; exported = attempt['diagnostic_export']
        assert child['baseline_copies'] == 23 and child['parameters']['max_outcomes'] == 16
        actual = audit_frontier(data,baseline,child,P/exported['path'])
        assert dict(actual) == exported['record_counts']; counts.update(actual)
    assert (counts['immutable_path_label'],counts['open'],counts['unfinished_expansion']) == (10727,5,2)
    folder = ROOT/'outputs/stage2-root-tree-pair-cap-ca93'; folder.mkdir(exist_ok=True)
    command = "import sys,unittest;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import tests.test_tree_pair_wrapper_cap as t;t.ROOT=Path(sys.argv[2]);r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(t));sys.exit(not r.wasSuccessful())"
    proc = subprocess.run(['python','-c',command,str(d/'src'),str(P)],capture_output=True,text=True,timeout=30)
    (folder/'tests.stdout').write_text(proc.stdout,encoding='utf-8'); (folder/'tests.stderr').write_text(proc.stderr,encoding='utf-8')
    assert proc.returncode == 0 and 'Ran 6 tests' in proc.stderr and '\nOK\n' in proc.stderr
    result = dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(d/'report.json'),
        actual_original_inputs=1,actual_complete_proposals=119,actual_pairs=19,processed_states=10722,
        before_copies=23,after_copies=22,historical_dp_copies=21,relative_DP_regression_retained=True,
        actual_full_output_replays=122,synthetic_witness_replays=98,total_full_replays=full,
        immutable_labels_replayed=10727,actual_open_prefixes=5,actual_unfinished_prefixes=2,
        root_contract_tests=6,root_contract_exit=proc.returncode,wrapper_diff_hunks=3,
        outlet_limited_parents=[61,59],scope='Only wrapper dispatch/statistics changed. All119 real proposals+baseline/best/oldDP and98 clearly synthetic witnesses independently replayed; all10727 real labels/5OPEN/2unfinished advanced from original physical prefix. Actual ca93 improves23to22, remains worse than old21, all19pairs tried and cap partial retained. No336/default/officialLevel or timing speedup claim.')
    (ROOT/'outputs/stage2-root-tree-pair-cap-ca93.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__ == '__main__': main()
