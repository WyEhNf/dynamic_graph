"""Freeze and bounded local-branch design audit after original manual gold."""
import json
import time
from review_stage2_frontier_static_r55 import ROOT,P,sha,read

def main():
    d=P/'research/batch55'; freeze=read(d/'static-plan-freeze.json'); gold=read(d/'gold-declaration.json'); charge=read(d/'charged-work-design.json')
    assert sha(d/'static-plan-freeze.json')=='323ebf431c516e58a35a068ab0be15409c2f8c8b5d7075d448fad4f1ed62cb55'
    assert len(freeze['files'])==22
    for r in freeze['files']: assert sha(P/r['path'])==r['sha256'] and (P/r['path']).stat().st_size==r['bytes']
    assert not freeze['candidate_implemented'] and not freeze['live_handles']
    assert gold['total_controls']==freeze['denominator']==sum(r['count'] for r in gold['families'])==160
    assert [r['count'] for r in gold['families']]==[48,32,32,16,16,16]
    assert charge['unchanged_limits']==dict(cut_total=2000000,cut_plus_projection_total=16000000,closure_max=128,held_top=24,width=2,branching=2)
    assert len(charge['rows'])==23
    assert read(ROOT/'outputs/stage2-root-frontier-static-r55.json')['passed']
    assert read(ROOT/'outputs/stage2-root-frontier-manual-r55.json')['passed']
    result=dict(passed=True,reviewed_unix=time.time(),static_plan_freeze_sha256=sha(d/'static-plan-freeze.json'),frozen_files=22,
        predeclared_gold_controls=160,charge_table_rows=23,manual_original_controls=8,independent_manual_topological_orders=52,
        authorization='Implement sole failed-cut width2/branch2 repair from R51 and generate/freeze160 original controls with literal charge expectations before compilation/execution. Root source/charge/fixtures audit before GCC/UBSan/same12 functional.',
        scope='Same original prefix and completeC<=128, full externalDIRECT hold/user counts, exact two-word completed-mask only dedup with lower attained peak. Same2M/16M/128/top24 and old greedy successes retained; extra work may displace old successful whole candidates. Smallmanual counterexamples support order branching, not actual63 recovery or global feasibility/optimality; ordinaryR51/useropenTeX unchanged.')
    (ROOT/'outputs/stage2-root-frontier-plan-r55.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__': main()
