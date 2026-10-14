"""Root serial-plan verification using Python integers and no project imports."""
import hashlib
import itertools
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/27-aicore-streams'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    files = {
        'inputs': ROOT / 'outputs/stage2-shallow-r44-root-snapshot/inputs.json',
        'diagnostic': ROOT / 'outputs/stage2-shallow-r44-root-snapshot/diagnostic.json',
        'hard_corpus': PROJECT / 'data/hard-corpus-resumed.json',
        'old_default': PROJECT / 'reports/paired-hard-batch43-1-after.json',
    }
    inputs = {r['name']: r for r in json.loads(files['inputs'].read_text())['cases']}
    hard = {r['name']: r for r in json.loads(files['hard_corpus'].read_text())['cases']}
    old = {r['name']: r for r in json.loads(files['old_default'].read_text())['cases']}
    diagnostic = json.loads(files['diagnostic'].read_text())
    assert len(inputs) == len(diagnostic['cases']) == 26
    assert set(inputs) == {r['name'] for r in diagnostic['cases']}
    for name, case in inputs.items():
        assert set(case) == {'name', 'hardware', 'nodes', 'deadline_us', 'expected_feasible'}
        assert all(value == hard[name][key] for key, value in case.items())
        assert not old[name]['pass']
    checks = []
    for row in diagnostic['cases']:
        if not row['valid']:
            assert row['plan'] is None and not row['pass']
            continue
        case = inputs[row['name']]
        hardware = case['hardware']
        nodes = {node['id']: node for node in case['nodes']}
        assert len(nodes) == len(case['nodes'])
        streams = [stream['tasks'] for stream in row['plan']['streams'] if stream['tasks']]
        assert len(streams) == 1 and hardware['stream_num'] >= 1
        tasks = streams[0]
        assert sorted(t['op_id'] for t in tasks) == sorted(nodes)
        users = {key: 0 for key in nodes}
        for node in nodes.values():
            assert len(set(node['inputs'])) == len(node['inputs'])
            for parent in node['inputs']:
                users[parent] += 1
        live = peak = elapsed = 0
        completed = set()
        for task in tasks:
            assert task['wait_before'] == [] and task['record_after'] == -1
            node = nodes[task['op_id']]
            assert all(parent in completed for parent in node['inputs'])
            assert node['core_type'] in ('AIC', 'AIV')
            pool = hardware['aic_core_num' if node['core_type'] == 'AIC' else 'aiv_core_num']
            assert 1 <= node['core_num'] <= min(pool, 128)
            assert 1 <= node['exec_time'] <= 1000000000
            assert node['workspace_memory'] >= 0 and node['output_memory'] >= 0
            # Workspace and output are both allocated at BEGIN. At END only
            # workspace and exhausted direct parents are freed; sinks persist.
            peak = max(peak, live + node['workspace_memory'] + node['output_memory'])
            assert peak <= hardware['memory_limit']
            elapsed += node['exec_time']
            live += node['output_memory']
            for parent in node['inputs']:
                users[parent] -= 1
                if users[parent] == 0:
                    live -= nodes[parent]['output_memory']
            assert live >= 0
            completed.add(node['id'])
        assert elapsed == row['T'] and peak == row['peak_memory'] == row['best_peak_lo']
        assert row['best_peak_hi'] == 0
        assert elapsed <= case['deadline_us'] and row['pass']
        assert live == sum(node['output_memory'] for key, node in nodes.items() if users[key] == 0 and not any(key in child['inputs'] for child in nodes.values()))
        checks.append(dict(name=row['name'], nodes=len(nodes), T=elapsed, peak=peak,
                           capacity=hardware['memory_limit'], final_sink_memory=live,
                           old_default_pass=old[row['name']]['pass']))
    assert len(checks) == 2
    exchange_checks = 0
    for wa, wb, oa, ob, initial in itertools.product(range(7), range(7), range(7), range(7), range(3)):
        if wa < wb:
            continue
        ab = max(initial + wa + oa, initial + oa + wb + ob)
        ba = max(initial + wb + ob, initial + ob + wa + oa)
        assert ab <= ba
        exchange_checks += 1
    # Independent prefix outputs: a(W20,O0) exhausts a 1-byte prefix;
    # b(W10,O0) exhausts a 100-byte prefix. Descending-W is worse here.
    prefix_ab = max(101 + 20, 100 + 10)
    prefix_ba = max(101 + 10, 1 + 20)
    assert prefix_ab == 121 and prefix_ba == 111 and prefix_ab > prefix_ba
    result = dict(reviewed_unix=time.time(), passed=True, recovered_records=2,
                  recovered_topologies=1, checks=checks, exchange_checks=exchange_checks,
                  method='Root reads actual saved serial plans and raw unchanged hard-corpus inputs, uses arbitrary-precision integers to reconstruct every BEGIN allocation/END release, direct parent lifetime, sinks retained through T, core pools, exact node permutation and deadline. No C++ simulator or project code imported.',
                  producer_exchange_proof='For constant initial live memory and independent newly opened producers whose outputs remain until consumer execution, W_a>=W_b makes both a,b peaks <= L+O_a+O_b+W_a, itself a lower bound on the b,a peak. Adjacent exchanges establish descending workspace order for that fixed segment only.',
                  prefix_counterexample=dict(descending_W_peak=prefix_ab, reverse_peak=prefix_ba,
                      implication='Prefix outputs released between producer executions invalidate constant-live exchange premise; no global optimality claim for that case.'),
                  limitation='Two recovered parameter records of one topology in an isolated preliminary26-input diagnostic. This is not complete202 regression, default promotion, throughput evidence, universal solvability, or official scoring.',
                  evidence={key: dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path)) for key, path in files.items()})
    destination = ROOT / 'outputs/stage2-root-shallow-recovery-r44.json'
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, recovered=2, exchange_checks=exchange_checks, checks=checks)))


if __name__ == '__main__':
    main()
