"""Root R177 producer/resource/frozen whole336 review before one R178 run."""
from collections import Counter
import json
import time
from review_stage2_tree_pair_cap_plan import ROOT,P,sha,read,rows,fingerprint

def main():
    d=P/'experiments/r177-anytime-full336-prepared'; prov=read(d/'source-provenance.json')
    assert prov['aggregate_source_sha256']=='a914cda38333a2d544db4bb868180ee008acfbf6d49c21ac73e0af9a7c9b5b56'
    for name,digest in prov['source_sha256'].items(): assert sha(P/name)==sha(d/'src'/name)==digest
    for name,digest in prov['historical_source_sha256'].items(): assert sha(P/name)==sha(d/name.split('\\')[-1])==digest
    for name,digest in prov['prepared_source_file_sha256'].items(): assert sha(d/name)==digest
    inputs=rows(d/'inputs.jsonl'); old=read(d/'report.json'); records={r['sha256']:r for r in old['records'] if r['variant']=='age_portfolio'}
    assert len(inputs)==len(records)==336 and {fingerprint(c['input']) for c in inputs}==records.keys()
    assert Counter(r['status'] for r in records.values())=={'verified':272,'proven_infeasible_under_model':47,'budget_exhausted':9,'scheduling_failure':8}
    assert sum(r.get('inserted_copies',0) for r in records.values())==192929
    assert len({c['family'] for c in inputs})==21
    assert prov['parameters']==dict(fixed_weight=2,total_time_budget_ms=500,cumulative_states=20000,outlets_each_pair=16,parent_max_nodes=96)
    resource=read(d/'resource-plan.json'); inventory=read(d/'static-inventory.json')
    eligible=[r for r in inventory['records'] if r['planned_route']=='search_eligible']
    assert len(eligible)==25
    diag=max((40000+len(r['eligible_parents']))*3072+len(r['eligible_parents'])*3072 for r in eligible)
    proposal=max(128*(r['baseline_physical_rows']+(2**r['bit_width'])*r['node_count'])+16*r['node_count']+65536 for r in eligible)
    assert diag==resource['conservative_one_input_diagnostic_bytes_max']==130799616
    assert proposal==resource['conservative_one_complete_output_bytes_max']==17493120
    assert diag+2*proposal+64*1024**2 < resource['reserve_bytes']==512*1024**2
    code=(P/'scripts/research_tree_pair_anytime_full336.py').read_text()
    assert "raise _Stop('producer_resource_reserve_after_saved_complete')" in code
    assert code.index('paths.append(path)')<code.index("raise _Stop('producer_resource_reserve_after_saved_complete')")
    assert "'full_input_quality_mean':None" in code and "assert len(prechecks)==272" in code and "assert len(records)==336" in code
    assert "snapshots[index]=None; del iterator,snapshot" in code and "snapshots.clear()" in code
    result=dict(passed=True,reviewed_unix=time.time(),prepared_provenance_sha256=sha(d/'source-provenance.json'),source_aggregate=prov['aggregate_source_sha256'],
        original_input_count=336,retained_legal=272,retained_model_certificates=47,retained_budget_failures=9,retained_scheduler_failures=8,
        initial_total_copies=192929,original_families=21,eligible_inputs=25,reserve_bytes=512*1024**2,
        current_input_diagnostic_envelope=diag,complete_file_envelope=proposal,
        authorization='One original whole336 --run with frozen wrapper/core/parameters and all272 baseline prechecks, complete proposals/finals independently checked. Preserve actual failure/partial evidence, no automatic rerun/default.',
        scope='Root read complete producer/resource contract and verified source/historical freezes. Existing core Stop used only after saving actual completed output; resource_unknown separately marks interruption, not infeasibility/timeout proof. Current-input diagnostic reserve bound does not guarantee global worst-case storage; timings are functional. No actual full336 candidate result yet.')
    (ROOT/'outputs/stage2-root-tree-pair-full336-plan.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__': main()
