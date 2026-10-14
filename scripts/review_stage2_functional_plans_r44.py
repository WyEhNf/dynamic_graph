"""Independent heap-event, bigint checker for actual R44 full-batch outputs."""
import hashlib
import heapq
import json
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/27-aicore-streams'
MAXIMUM = (1 << 63) - 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def simulate(case, plan):
    h = case['hardware']
    nodes = {n['id']: n for n in case['nodes']}
    streams = [s['tasks'] for s in plan['streams'] if s['tasks']]
    assert len(streams) <= h['stream_num']
    placements, events, waits = {}, {}, Counter()
    for stream, tasks in enumerate(streams):
        for offset, task in enumerate(tasks):
            key = task['op_id']
            assert key in nodes and key not in placements
            placements[key] = stream, offset, task['record_after']
            event = task['record_after']
            assert event >= -1
            if event >= 0:
                assert event not in events
                events[event] = key
            assert len(set(task['wait_before'])) == len(task['wait_before'])
            assert all(event >= 0 for event in task['wait_before'])
            waits.update(task['wait_before'])
    assert set(placements) == set(nodes) and set(events) == set(waits)
    users = Counter()
    for key, node in nodes.items():
        s, offset, _ = placements[key]
        task = streams[s][offset]
        assert all(event in events and placements[events[event]][0] != s for event in task['wait_before'])
        assert len(set(node['inputs'])) == len(node['inputs'])
        for parent in node['inputs']:
            ps, po, event = placements[parent]
            assert (po < offset) if ps == s else (event >= 0 and event in task['wait_before'])
            users[parent] += 1
    position = [0] * len(streams)
    phase = ['waiting'] * len(streams)
    timers, published, done = [], set(), set()
    core_use = Counter()
    memory = peak = now = last_compute = 0

    def timer(stream, delay, kind):
        assert 0 <= now + delay <= MAXIMUM
        heapq.heappush(timers, (now + delay, stream, kind))

    while len(done) < len(nodes):
        # Heap consumes every same-clock completion before any new allocation.
        while timers and timers[0][0] == now:
            _, stream, kind = heapq.heappop(timers)
            task = streams[stream][position[stream]]
            node = nodes[task['op_id']]
            if kind == 'wait':
                phase[stream] = 'ready'
            elif kind == 'record':
                published.add(task['record_after'])
                position[stream] += 1
                phase[stream] = 'waiting'
            else:
                assert kind == 'compute'
                core_use[node['core_type']] -= node['core_num']
                memory -= node['workspace_memory']
                done.add(node['id'])
                last_compute = now
                for parent in node['inputs']:
                    users[parent] -= 1
                    if users[parent] == 0:
                        memory -= nodes[parent]['output_memory']
                assert memory >= 0
                if task['record_after'] >= 0:
                    if h['event_record_time']:
                        phase[stream] = 'recording'
                        if len(done) < len(nodes):
                            timer(stream, h['event_record_time'], 'record')
                    else:
                        published.add(task['record_after'])
                        position[stream] += 1
                        phase[stream] = 'waiting'
                else:
                    position[stream] += 1
                    phase[stream] = 'waiting'
        if len(done) == len(nodes):
            break
        for stream, tasks in enumerate(streams):
            if position[stream] == len(tasks):
                continue
            task = tasks[position[stream]]
            if phase[stream] == 'waiting' and set(task['wait_before']) <= published:
                delay = len(task['wait_before']) * h['event_wait_time']
                if delay:
                    phase[stream] = 'wait_timer'
                    timer(stream, delay, 'wait')
                else:
                    phase[stream] = 'ready'
            if phase[stream] != 'ready':
                continue
            node = nodes[task['op_id']]
            assert node['core_type'] in ('AIC', 'AIV')
            capacity = h['aic_core_num' if node['core_type'] == 'AIC' else 'aiv_core_num']
            assert 1 <= node['core_num'] <= min(capacity, 128)
            assert node['workspace_memory'] >= 0 and node['output_memory'] >= 0
            assert 1 <= node['exec_time'] <= 1000000000
            allocation = node['workspace_memory'] + node['output_memory']
            if core_use[node['core_type']] + node['core_num'] > capacity or memory + allocation > h['memory_limit']:
                continue
            assert set(node['inputs']) <= done
            core_use[node['core_type']] += node['core_num']
            memory += allocation
            peak = max(peak, memory)
            phase[stream] = 'computing'
            timer(stream, node['exec_time'], 'compute')
        assert timers, 'Plan deadlocked'
        now = timers[0][0]
    assert last_compute <= case['deadline_us']
    return last_compute, peak


def main():
    specs = [
        ('hard', 'data/hard-corpus-resumed.json', 'reports/paired-hard-batch43-1-after.json', 'reports/hard-functional-batch44.json', 202, 139, 141),
        ('forkjoin', 'data/nested-forkjoin-new-batch38.json', 'reports/paired-forkjoin-batch43-1-after.json', 'reports/forkjoin-functional-batch44.json', 36, 36, 36),
        ('heldout', 'data/shallow-heldout-batch44.json', 'reports/heldout-before-functional-batch44.json', 'reports/heldout-after-functional-batch44.json', 72, 68, 72),
    ]
    results = []
    for name, input_file, before_file, after_file, count, before_count, after_count in specs:
        paths = {key: PROJECT / value for key, value in [('input', input_file), ('before', before_file), ('after', after_file)]}
        cases = {c['name']: c for c in json.loads(paths['input'].read_text())['cases']}
        before = {c['name']: c for c in json.loads(paths['before'].read_text())['cases']}
        after = {c['name']: c for c in json.loads(paths['after'].read_text())['cases']}
        assert set(cases) == set(before) == set(after) and len(cases) == count
        assert sum(c['pass'] for c in before.values()) == before_count
        assert sum(c['pass'] for c in after.values()) == after_count
        recovered, validated = [], 0
        for key, row in after.items():
            assert row['models_equal']
            assert not before[key]['pass'] or row['pass']
            if not row['pass']:
                continue
            assert row['valid']
            T, peak = simulate(cases[key], row['plan'])
            assert (T, peak) == (row['T'], row['peak_memory'])
            validated += 1
            if before[key]['pass']:
                assert (T, peak) == (before[key]['T'], before[key]['peak_memory'])
            else:
                recovered.append(dict(name=key, T=T, peak=peak, nonempty_streams=sum(bool(s['tasks']) for s in row['plan']['streams'])))
        results.append(dict(suite=name, records=count, before_legal=before_count, after_legal=after_count,
                            independently_validated=validated, recovered=recovered, lost=0,
                            evidence={key: dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path)) for key, path in paths.items()}))
    result = dict(reviewed_unix=time.time(), passed=True, independently_validated=249,
                  recovered_records=6, suites=results,
                  method='Root independent Python heap-event simulation, no project imports. All249 saved passing plans checked: exact original node coverage, explicit direct cross-stream events, wait/record durations, compressed stream start order, simultaneous completions before allocations, separate core pools, W+O at BEGIN, direct-last-consumer END releases, sink lifetime and T excludes final Record. Arbitrary-precision memory and checked int64 timestamps.',
                  limitation='Local synthetic310-input functional evidence.61 original witness-feasible hard cases still fail. These functional binaries use different O2/O3 flags, so no causal performance comparison, default promotion or official score claim.')
    (ROOT / 'outputs/stage2-root-functional-plans-r44.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, independently_validated=249, recovered=6,
                         suites=[{k:v for k,v in r.items() if k!='evidence'} for r in results])))


if __name__ == '__main__':
    main()
