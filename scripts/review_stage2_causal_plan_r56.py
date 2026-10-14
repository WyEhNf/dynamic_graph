"""Review literal full-graph counterexamples and causal restart design."""
import json,time
from review_stage2_causal_attribution_r56 import ROOT,P,read,sha
from review_stage2_functional_plans_r44 import simulate
def main():
    d=P/'research/batch56';m=read(d/'static-plan-freeze.json')
    assert sha(d/'static-plan-freeze.json')=='1524ccf81fb17c29bc656cf3d7bc3eb4cecf2a8f005ed14a99924bf8af09c823'
    for row in m['files']:assert sha(P/row['path'])==row['sha256'] and (P/row['path']).stat().st_size==row['bytes']
    attribution=read(ROOT/'outputs/stage2-root-causal-attribution-r56.json');assert attribution['passed']
    manual=read(d/'causal-deferral-manual-original.json');good=bad=0
    for case in manual['cases']:
        try:
            T,peak=simulate(case,case['fixed_plan'])
        except AssertionError:
            assert not case['expected_valid'];bad+=1
        else:
            assert case['expected_valid'] and T==case['T'] and peak==case['peak'];good+=1
    assert (good,bad)==(7,5)
    controls={r['name']:r for r in manual['cases']}
    assert controls['premature-P']['trace'][-1]['memory']==130 and controls['delay-P']['peak']==100
    assert controls['MAX-premature-P']['trace'][-1]['memory']>2**63-1
    plan=(d/'static-design.md').read_text(encoding='utf-8')
    for term in ['unfinished','2M','16M','128/top24','不同','尚未ready','一次restart']:
        assert term in plan
    declared=read(d/'gold-declaration.json');assert declared['planned_cases']==160 and sum(declared['family_counts'].values())==160
    result=dict(passed=True,reviewed_unix=time.time(),static_freeze_sha256=sha(d/'static-plan-freeze.json'),frozen_files=len(m['files']),independent_full_manual_plans=12,legal_plans=good,invalid_plans=bad,strict_prefix_failures=2,planned_gold=160,
        authorization='Implement isolated R56 source-only one charged original-input causal j-before-p restart plus160 predeclared full-original gold and literal charge boundary freeze; rootreview source/gold/fee before compile or solver. Start from exactR51, not R55 repair. No63 expansion/default/TeX changes.',
        scope='Full original-node physical counterexamples and necessary-bound causal rationale accepted. Unfinished-not-ready target scan, acyclic voluntary ordering with unchanged original degrees/users/lifetimes, single restart under shared2M/16M, full fee accounting required. Actual new algorithm recovery/performance remains unproven.')
    (ROOT/'outputs/stage2-root-causal-plan-r56.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
