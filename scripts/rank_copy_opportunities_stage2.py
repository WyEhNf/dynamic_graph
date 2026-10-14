"""Rank verified R91 cases by possible ratio reduction, preserving all states.

A necessary bound is not an attainable optimum. Rankings are research guidance,
not a Level score or evidence that any candidate reaches the bound.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
result_path = root/'outputs/stage2-copy-opportunity.json'
if result_path.exists():
    raise SystemExit('Refusing to replace previous opportunity audit')

input_paths = [root/'projects/18-isa-scheduler/experiments'/relative for relative in (
    'milestone-level-r91-336/report.json', 'r93-dag-persistent-audit/report.json')]
milestone, bounds = [json.loads(p.read_text(encoding='utf-8')) for p in input_paths]
current = {r['sha256']: r for r in milestone['records'] if r['variant']=='research_portfolio'}
assert len(current) == 336
rows = []
families = defaultdict(list)
states = defaultdict(int)
for bound in bounds['records']:
    record = current[bound['sha256']]
    assert record['status'] == bound['previous_status']
    states[record['status']] += 1
    if record['status'] != 'verified':
        continue
    n = record['node_count']
    copies = record['inserted_copies']
    lower = bound['copy_lower_bound']
    assert n == bound['original_nodes'] and 0 <= lower <= copies
    assert record['output_count'] == n+copies
    actual_ratio = copies/(n+copies)
    lower_ratio = lower/(n+lower)
    row = dict(sha256=record['sha256'], block_id=record['block_id'],
               family=record['family'], bit_width=record['bit_width'], n=n,
               actual_copy=copies, necessary_copy_lower_bound=lower,
               actual_copy_output_ratio=actual_ratio,
               necessary_copy_output_ratio=lower_ratio,
               maximum_possible_ratio_reduction=actual_ratio-lower_ratio)
    rows.append(row)
    families[row['family']].append(row)
assert len(rows) == 272 and sum(states.values()) == 336
aggregate = []
for name, values in families.items():
    aggregate.append(dict(family=name, verified_count=len(values),
                          contribution_to_272_mean=sum(r['maximum_possible_ratio_reduction'] for r in values)/272,
                          actual_mean=sum(r['actual_copy_output_ratio'] for r in values)/len(values),
                          necessary_lower_mean=sum(r['necessary_copy_output_ratio'] for r in values)/len(values)))
aggregate.sort(key=lambda r:r['contribution_to_272_mean'], reverse=True)
rows.sort(key=lambda r:r['maximum_possible_ratio_reduction'], reverse=True)
report = dict(scope='Research guidance for all 272 R91 verified cases; all 336 input statuses retained. Necessary bounds may be loose, so gaps are upper bounds on achievable reduction.',
              statuses=dict(states), verified=272,
              actual_successful_subset_mean=sum(r['actual_copy_output_ratio'] for r in rows)/272,
              necessary_successful_subset_lower_mean=sum(r['necessary_copy_output_ratio'] for r in rows)/272,
              families=aggregate, cases=rows,
              evidence=[dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in input_paths],
              source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
result_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(statuses=report['statuses'],families=aggregate[:8],top_cases=rows[:8]),ensure_ascii=False))
