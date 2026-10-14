"""Necessary future-BEGIN bounds for actual completed serial prefixes.

Original DIRECT edges only; Python big integers; no witness, solver or mutation.
An obstructed prefix is not an infeasible graph. A passing bound is not a plan.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path


class WorkExhausted(Exception):
    pass


def analyze_prefix(nodes, prefix, memory_limit, *, work_limit=1000000):
    if type(work_limit) is not int or work_limit < 1:
        raise ValueError('positive work budget required')
    if type(memory_limit) is not int or memory_limit < 0:
        raise ValueError('invalid memory capacity')
    by_id = {node['id']: node for node in nodes}
    if len(by_id) != len(nodes): raise ValueError('duplicate node IDs')
    outgoing = {key: [] for key in by_id}
    for node in nodes:
        for name in ('workspace_memory', 'output_memory'):
            if type(node[name]) is not int or node[name] < 0: raise ValueError('invalid memory request')
        if len(set(node['inputs'])) != len(node['inputs']): raise ValueError('duplicate DIRECT input')
        for parent in node['inputs']:
            if parent not in by_id: raise ValueError('missing DIRECT input')
            outgoing[parent].append(node['id'])
    # Validate the whole DAG, including components beyond this saved prefix.
    degrees = {key: len(node['inputs']) for key, node in by_id.items()}
    ready = deque(key for key in by_id if degrees[key] == 0)
    visited = 0
    while ready:
        key = ready.popleft(); visited += 1
        for child in outgoing[key]:
            degrees[child] -= 1
            if degrees[child] == 0: ready.append(child)
    if visited != len(nodes): raise ValueError('cyclic input graph')
    done = set()
    for key in prefix:
        if key not in by_id or key in done or not set(by_id[key]['inputs']) <= done:
            raise ValueError('saved prefix is not a unique topological prefix')
        done.add(key)
    held = [key for key in by_id if key in done and
            (not outgoing[key] or any(child not in done for child in outgoing[key]))]
    live = sum(by_id[key]['output_memory'] for key in held)
    ready = [{'id': key, 'BEGIN_memory': live + node['workspace_memory'] + node['output_memory'],
              'memory_fit': live + node['workspace_memory'] + node['output_memory'] <= memory_limit}
             for key, node in by_id.items() if key not in done and set(node['inputs']) <= done]
    work = 0
    def charge():
        nonlocal work
        if work >= work_limit: raise WorkExhausted()
        work += 1
    def closure(start, edges):
        seen, pending = {start}, [start]
        while pending:
            charge(); key = pending.pop()
            for child in edges[key]:
                charge()
                if child not in seen: seen.add(child); pending.append(child)
        return seen
    incoming = {key: node['inputs'] for key, node in by_id.items()}
    certificates = []
    checked = []
    status = 'ALL_UNFINISHED_TARGETS_CHECKED'
    try:
        for target, node in by_id.items():
            if target in done: continue
            ancestors = closure(target, incoming) - {target}
            descendants = closure(target, outgoing)
            forced = []
            for producer, value in by_id.items():
                charge()
                if producer == target or producer not in ancestors | done or not value['output_memory']:
                    continue
                pinned_users = []
                for child in outgoing[producer]:
                    charge()
                    if child in descendants: pinned_users.append(child)
                if not outgoing[producer] or pinned_users:
                    forced.append({'id': producer, 'output_memory': value['output_memory'],
                        'strict_ancestor': producer in ancestors, 'sink': not outgoing[producer],
                        'pinned_DIRECT_users': pinned_users})
            bound = node['workspace_memory'] + node['output_memory'] + sum(p['output_memory'] for p in forced)
            checked.append(target)
            if bound <= memory_limit: continue
            base = node['workspace_memory'] + node['output_memory'] + sum(p['output_memory'] for p in forced if p['strict_ancestor'])
            extra_ids = {p['id'] for p in forced if not p['strict_ancestor']}
            cumulative = base
            first_crossing = {'prefix_length': 0, 'producer_id': None} if base > memory_limit else None
            extras = []
            for index, producer in enumerate(prefix):
                if producer in extra_ids:
                    extras.append(producer); cumulative += by_id[producer]['output_memory']
                    if first_crossing is None and cumulative > memory_limit:
                        first_crossing = {'prefix_length': index + 1, 'producer_id': producer}
            # Deletion-minimal extra cover, not an optimal set or feasible repair.
            cover = list(extras)
            cover_bound = bound
            for producer in sorted(extras, key=lambda key: (by_id[key]['output_memory'], prefix.index(key))):
                value = by_id[producer]['output_memory']
                if cover_bound - value > memory_limit:
                    cover.remove(producer); cover_bound -= value
            certificates.append({'target_id': target, 'necessary_BEGIN_bound': bound,
                'memory_limit': memory_limit, 'intrinsic_ancestor_bound': base,
                'forced_outputs': forced, 'earliest_obstructed_prefix': first_crossing,
                'irreducible_extra_cover_ids': cover, 'cover_bound': cover_bound,
                'consequence': 'At least one covered completed-producer decision must change before this target can fit.'
                    if cover else 'Intrinsic ancestor bound already exceeds capacity under original single-execution semantics.'})
    except WorkExhausted:
        status = 'PARTIAL_WORK_BUDGET_UNKNOWN_TARGETS'
    return {'status': status, 'charged_work': work, 'work_limit': work_limit,
        'checked_target_ids': checked, 'unchecked_target_ids': [key for key in by_id if key not in done and key not in checked],
        'live_output_memory': live, 'held_output_ids': held, 'ready_nodes': ready,
        'certificates': certificates, 'prefix_length': len(prefix),
        'scope': 'Necessary future target BEGIN bounds; unchanged prefix only; no CPU-performance or recovery claim.'}


def analyze_observers(input_path, observer_path):
    inputs = {case['name']: case for case in json.loads(input_path.read_text())['cases']}
    observed = json.loads(observer_path.read_text())['cases']
    records = []
    for case in observed:
        original = inputs[case['name']]
        for scope in ('helper_observer', 'whole_observer'):
            observation = case[scope]
            for index, state in enumerate(observation['states']):
                original_ids = {node['id'] for node in original['nodes']}
                if state['n'] != len(original_ids) or len(state['original_ids']) != len(original_ids) or set(state['original_ids']) != original_ids:
                    raise AssertionError('saved original-ID inventory differs from original graph')
                result = analyze_prefix(original['nodes'], state['prefix_ids'], original['hardware']['memory_limit'])
                if result['live_output_memory'] != state['live']:
                    raise AssertionError('original DIRECT-edge live memory differs from actual observer')
                ids = state['original_ids']; done = set(state['prefix_ids'])
                for key, flag, degree, users in zip(ids, state['done'], state['degree'], state['users'], strict=True):
                    node = next(node for node in original['nodes'] if node['id'] == key)
                    expected_users = sum(key in n['inputs'] and n['id'] not in done for n in original['nodes'])
                    if flag not in (0, 1) or bool(flag) != (key in done) or degree != sum(p not in done for p in node['inputs']) or users != expected_users:
                        raise AssertionError('saved done/degree/users differs from original graph')
                records.append({'name': case['name'], 'observer_scope': scope, 'saved_state_index': index,
                    'prefix_ids_sha256': hashlib.sha256(json.dumps(state['prefix_ids'], separators=(',', ':')).encode()).hexdigest(),
                    'stage': state['stage'], 'states_dropped': observation['states_dropped'], **result})
    return {'records': records, 'count': len(records), 'original_cases': len(observed),
        'obstructed_prefixes': sum(bool(row['certificates']) for row in records),
        'certificates': sum(len(row['certificates']) for row in records),
        'distinct_saved_prefixes': len({(row['name'], row['prefix_ids_sha256']) for row in records}),
        'distinct_obstructed_prefixes': len({(row['name'], row['prefix_ids_sha256']) for row in records if row['certificates']}),
        'distinct_obstructed_input_records': len({row['name'] for row in records if row['certificates']}),
        'source_input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'source_observer_sha256': hashlib.sha256(observer_path.read_bytes()).hexdigest(),
        'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'default_changed': False, 'solver_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--observer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze_observers(args.inputs, args.observer)
    with args.output.open('x', encoding='utf-8') as stream: json.dump(result, stream, indent=2)
    print(json.dumps({key: result[key] for key in ('count', 'original_cases', 'obstructed_prefixes', 'certificates')}))
