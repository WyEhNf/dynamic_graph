"""Freeze review of the fixed81 initial/oracle/fullproposal/frontier producer."""
import ast,json,time
from review_stage2_general_region_source_r183 import ROOT,P,D,sha
def main():
    folder=P/'experiments/r184-general-region-functional-prepared'
    m=json.loads((folder/'source-provenance.json').read_text(encoding='utf-8'))
    assert m['source_aggregate_sha256']=='76b97adda035cbb1ab30575cc24f9903da5351f01fe320bda58b2f76b3cd78df'
    assert m['frozen_R183_manifest_sha256']==sha(D/'source-provenance.json')
    for name,digest in m['source_sha256'].items():
        assert sha(P/name)==sha(folder/'src'/name)==digest
        if name.endswith('.py'):ast.parse((P/name).read_text(encoding='utf-8'))
    for name,digest in m['prepared_sha256'].items():assert sha(folder/name)==digest
    assert sha(folder/'raw80.jsonl')==sha(D/'inputs.jsonl')
    cases=[json.loads(line) for line in (folder/'cases.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(cases)==81 and sum(c['kind']=='tiny_frozen' for c in cases)==80
    hand=json.loads((folder/'hand11.json').read_text(encoding='utf-8'))
    assert cases[-1]['input']==hand['input'] and hand['baseline']['copies']==3
    params=m['parameters'];assert params['search_ms']==params['raw_oracle_ms']==500
    assert params['search_transitions']==params['raw_oracle_expansions']==params['raw_oracle_discovered']==20000
    independent=ast.parse((P/'scripts/general_region_raw_checks.py').read_text(encoding='utf-8'))
    for node in ast.walk(independent):
        if isinstance(node,ast.ImportFrom):assert not (node.module or '').startswith('isa_scheduler')
    code=(P/'scripts/research_general_region_isolated.py').read_text(encoding='utf-8')
    for fragment in ['stream.flush()','four_check(data,candidate)','export_and_replay(data,initial,result','automatic_restart','process_peak_working_set_bytes','local_semantics_not_official']:
        assert fragment in code
    result=dict(passed=True,reviewed_unix=time.time(),manifest_sha256=sha(folder/'source-provenance.json'),source_files=len(m['source_sha256']),fixed_inputs=81,tiny_raw_oracle_inputs=80,handwritten_N11=1,
        authorization='Execute fixedR18581inputs once after project19 cost window finishes. Preserve all unknown/partial/failures, all wholeproposals and immutable/frontier physical replay. No full336/default change.',
        scope='Frozen complete runner+independent original-ring replay reviewed. Initial construction independent of broadraw costoracle; allactual sink proposals saved before post-search physical/symbolic/sixinteger checks; processlifetime peak scope explicit. Algorithm quality and Level remain unproven until actual results audited.')
    (ROOT/'outputs/stage2-root-general-region-runner-r184.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
