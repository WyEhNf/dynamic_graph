"""Reexecute the drained-state oracle using independent raw-set floor arithmetic."""
import hashlib
import importlib.util
import json
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/18-isa-scheduler'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_sets(data):
    rows = data['instructions']
    ancestors, users = [], [set() for _ in rows]
    for node, row in enumerate(rows):
        upstream = set()
        for token in row.get('inputs', []):
            parent = node - int(token[2:])
            assert 0 <= parent < node and rows[parent]['op'] != 'SET'
            upstream.add(parent)
            upstream.update(ancestors[parent])
            users[parent].add(node)
        ancestors.append(upstream)
    cones = [set().union(*(ancestors[c] | {c} for c in users[node])) for node in range(len(rows))]
    roots = [node for node, row in enumerate(rows) if row['op'] == 'GET']
    cores = {root: {node for node in range(len(rows)) if root in ancestors[node] and
                    any(node in ancestors[c] for c in users[root])} for root in roots}
    return users, cones, cores, roots


def main():
    source = PROJECT / 'scripts/research_lifetime_state_audit.py'
    spec = importlib.util.spec_from_file_location('reviewed_state_oracle', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    totals, evidence = {}, {}
    for name in ('r136-lifetime-state-oracle', 'r137-lifetime-negative-state'):
        directory = PROJECT / 'experiments' / name
        report = json.loads((directory / 'report.json').read_text())
        wrappers = [json.loads(line) for line in (directory / 'inputs.jsonl').read_text().splitlines()]
        assert len(wrappers) == len(report['records']) == report['count']
        assert sha(directory / 'inputs.jsonl') == report['corpus_sha256']
        for filename, expected in report['source_sha256'].items():
            assert sha(PROJECT / filename) == expected
        observed_records = []
        for wrapper, old in zip(wrappers, report['records']):
            data = wrapper['input']
            users, raw_cones, raw_cores, raw_roots = raw_sets(data)
            def independent_floor(ages, born, remaining, roots, root_slot, cones, cores, completed, window):
                assert roots == raw_roots and window == 2 ** data['bit_width'] and window >= 2
                assert cones == [sum(1 << node for node in s) for s in raw_cones]
                assert cores == {root: sum(1 << node for node in s) for root, s in raw_cores.items()}
                assert all(remaining[slot] == sum(not (completed >> c & 1) for c in users[root])
                           for slot, root in enumerate(roots))
                assert all(bool(born >> slot & 1) == bool(completed >> root & 1) for slot, root in enumerate(roots))
                result = 0
                def ceil_div(value):
                    return max(0, -(-value // (window - 1)))
                for identity, age in ages:
                    assert completed >> identity & 1 and 1 <= age <= window
                    pending = sum(not (completed >> node & 1) for node in raw_cones[identity])
                    result += ceil_div(age + pending - window - 1)
                for slot, root in enumerate(roots):
                    if remaining[slot] and not (born >> slot & 1):
                        result += ceil_div(len(raw_cores[root]) + 1 - window)
                return result
            module.lifetime_floor = independent_floor
            observed = module.audit(data, budget_ms=10000, max_states=20000)
            assert not observed.get('violations')
            assert observed['status'] == old['status']
            for field in ('states', 'edges', 'finite_remaining_states', 'dead_remaining_states',
                          'positive_floor_states', 'max_floor', 'initial_optimum'):
                assert observed.get(field) == old.get(field), (name, wrapper.get('seed'), field)
            observed_records.append(observed)
        totals[name] = dict(inputs=len(wrappers), statuses=dict(Counter(r['status'] for r in observed_records)),
                           finite_states=sum(r.get('finite_remaining_states', 0) for r in observed_records),
                           positive_floor_states=sum(r.get('positive_floor_states', 0) for r in observed_records),
                           dead_states=sum(r.get('dead_remaining_states', 0) for r in observed_records),
                           contradictions=0)
        for filename in ('report.json', 'inputs.jsonl'):
            path = directory / filename
            evidence[path.relative_to(ROOT).as_posix()] = sha(path)
    result = dict(passed=True, reviewed_unix=time.time(), suites=totals, evidence=evidence,
                  oracle_source_sha256=sha(source),
                  scope='Actual oracle reexecution with independently constructed raw ancestor sets, consumer cones, '
                        'strict GET cores and replacement floor arithmetic. All finite remaining states compared to '
                        'reverse exact COPY costs; same reviewed physical-age transition oracle reused, not an independent '
                        'second transition engine.12 closed-infeasible graphs and1344 dead prefixes retained. '
                        'Necessary remaining-COPY floor only; no real corpus quality or official Level result.')
    (ROOT / 'outputs/stage2-root-lifetime-floor.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
