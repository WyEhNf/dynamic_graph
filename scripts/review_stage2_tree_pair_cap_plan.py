"""Review saved regression attribution and wrapper-only cap continuation plan."""
from collections import Counter
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'projects/18-isa-scheduler'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path): return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]
def fingerprint(data): return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def main():
    for stage in ('r173-anytime-ca93-static', 'r174-anytime-full336-static'):
        folder = P / 'experiments' / stage
        prov = read(folder / 'source-provenance.json')
        for name, digest in prov['source_sha256'].items():
            assert sha(folder / 'src' / name) == digest
        for name, digest in prov['read_only_evidence_sha256'].items():
            assert sha(P / name) == digest, name
    frozen = read(P / 'experiments/r174-anytime-full336-static/static-evidence-provenance.json')
    for name, digest in frozen['evidence_sha256'].items(): assert sha(P / name) == digest
    coverage = read(P / 'experiments/r174-anytime-full336-static/report.json')
    source = P / 'experiments/r107-age-portfolio-336'
    historical = read(source / 'report.json')
    before = {r['sha256']:r for r in historical['records'] if r['variant'] == 'age_portfolio'}
    inputs = rows(source / 'inputs.jsonl')
    assert len(inputs) == len(coverage['records']) == 336
    for case, row in zip(inputs, coverage['records']):
        key = fingerprint(case['input'])
        assert key == row['sha256'] and row['family'] == case['family']
        assert before[key]['status'] == row['before_status']
        assert before[key].get('inserted_copies') == row['before_copies']
    status = Counter(r['before_status'] for r in coverage['records'])
    assert status == {'verified':272, 'proven_infeasible_under_model':47, 'budget_exhausted':9, 'scheduling_failure':8}
    assert sum(r['before_copies'] for r in coverage['records'] if r['before_status']=='verified') == 192929
    assert Counter(r['planned_route'] for r in coverage['records']) == coverage['planned_routes']
    assert coverage['planned_routes']['search_eligible'] == 25
    assert sum(len(r['eligible_parents']) for r in coverage['records']) == 7714
    a = read(P / 'experiments/r173-anytime-ca93-static/report.json')
    assert (a['initial_copies'], a['old_dp_copies'], a['awa_copies']) == (23,21,23)
    assert a['processed_states'] == 7580 and a['wrapper_search_elapsed_ms'] < 500
    assert [(r['parent'],r['outcome'],r['complete_outputs']) for r in a['actual_attempts']] == [(62,'exhausted_improvement_search',0),(61,'partial_outlet_limit',16)]
    assert len(a['all_complete_proposals']) == 16
    assert min(r['actual_copies'] for r in a['all_complete_proposals']) == 24
    assert not any(r['dp21_witness_within_fixed_side_orders'] for r in a['actual_attempts'])
    new = P / 'experiments/r175-anytime-pair-cap-static'
    prov = read(new / 'source-provenance.json')
    for name, digest in prov['source_sha256'].items(): assert sha(P/name) == digest
    assert all(prov['r172_core_and_wrapper_still_identical'].values())
    assert sha(P / 'research/level-stage/tree-pair-outlet-wrapper-plan.md') == '8da42eea149c2e0e637a81987d13b7f6ec69cec48e33df1c4b4b97718ac9d742'
    result = dict(passed=True, reviewed_unix=time.time(), cap_plan_sha256=sha(P/'research/level-stage/tree-pair-outlet-wrapper-plan.md'),
        full336_static_report_sha256=sha(P/'experiments/r174-anytime-full336-static/report.json'),
        full_input_count=336, retained_statuses=dict(status), before_success_copies=192929,
        static_eligible_inputs=25, static_eligible_pairs=7714, saved_ca93_states=7580, saved_ca93_outlets=16,
        authorization='Wrapper-only outcome dispatch/statistics and synthetic control tests; then one original ca93 actual candidate with all complete proposals and raw diagnostics retained and independently verified. No full336/baseline/default run.',
        scope='Saved16 proposals and full336 baseline lineage accepted; particular old21 order is outside first two families, not proof of no alternative21. Continue after per-pair cap using same total deadline/state budget and initial incumbent, retain overall partial. Old454MB estimate is historical only; re-evaluate storage before full336.')
    (ROOT/'outputs/stage2-root-tree-pair-cap-plan.json').write_text(json.dumps(result,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))

if __name__ == '__main__': main()
