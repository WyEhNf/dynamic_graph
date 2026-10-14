"""Independent exact serial gold under near-INT64_MAX memory scaling.

This oracle evaluates direct edges and result release with Python integers.
It imports neither submission nor local verifier and never reads solver output.
"""
import copy
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root/'projects/27-aicore-streams/data/hard-corpus-resumed.json'
destination = root/'outputs/stage2-memory-structure/scaled-serial-controls.json'
if destination.exists():
    raise SystemExit('Refusing to overwrite generated controls')
maximum = (1 << 63)-1
controls = []
for raw in json.loads(source.read_text(encoding='utf-8'))['cases']:
    streams = raw['witness_plan']['streams']
    if len(streams) != 1 or len(raw['nodes']) > 200:
        continue
    tasks = streams[0]['tasks']
    if any(t['wait_before'] or t['record_after'] != -1 for t in tasks):
        continue
    case = copy.deepcopy(raw)
    original_capacity = case['hardware']['memory_limit']
    if original_capacity <= 0:
        continue
    multiplier = maximum//original_capacity
    assert multiplier > original_capacity
    case['hardware']['memory_limit'] = maximum
    case['name'] = 'scaled_int64_'+case['name']
    for node in case['nodes']:
        for field in ('workspace_memory', 'output_memory'):
            node[field] *= multiplier
            assert 0 <= node[field] <= maximum
    nodes = {n['id']: n for n in case['nodes']}
    users = {i: 0 for i in nodes}
    for node in nodes.values():
        assert len(node['inputs']) == len(set(node['inputs']))
        for parent in node['inputs']:
            users[parent] += 1
    done = set()
    live = peak = elapsed = 0
    for task in tasks:
        node = nodes[task['op_id']]
        assert node['id'] not in done and set(node['inputs']) <= done
        during = live+node['workspace_memory']+node['output_memory']
        peak = max(peak, during)
        assert during <= maximum
        live += node['output_memory']
        for parent in node['inputs']:
            users[parent] -= 1
            if users[parent] == 0:
                live -= nodes[parent]['output_memory']
        assert live >= 0
        done.add(node['id'])
        elapsed += node['exec_time']
    assert done == set(nodes)
    assert peak == raw['generation']['witness_peak']*multiplier
    assert elapsed == raw['generation']['witness_T']
    case['fixed_plan'] = copy.deepcopy(case['witness_plan'])
    case['gold_valid'] = True
    case['gold_T'] = elapsed
    case['gold_peak'] = peak
    case['generation'] = dict(original=raw['name'],scale=multiplier,
                              witness_T=elapsed,witness_peak=peak,
                              exact_scaling='All positive memory values scaled uniformly. Capacity has a residual smaller than one scaled memory unit, preserving every memory feasibility inequality.',
                              historical_output_sum=str(sum(n['output_memory'] for n in nodes.values())))
    controls.append(case)
    if len(controls) == 32:
        break
assert len(controls) == 32
report = dict(format='aicore-local-v1',cases=controls,
              gold_scope='Exact serial original edges, Begin W+O allocation, direct last-consumer End release, sinks retained. No Event gold; no solver completeness claim.',
              source_suite_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(path=destination.as_posix(),controls=len(controls),
                      history_sums_exceed_max=sum(int(c['generation']['historical_output_sum'])>maximum for c in controls)),ensure_ascii=False))
