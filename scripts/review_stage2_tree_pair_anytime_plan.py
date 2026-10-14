"""Root read-only budget attribution and proposed full-output search review."""
import json
import math
import time
from collections import Counter
from review_stage2_tree_pair_warmstart_84 import ROOT,P,D,sha


def main():
    static=P/'experiments/r166-tree-pair-static-budget'
    read=lambda path:json.loads(path.read_text())
    provenance=read(static/'provenance.json')
    for name,digest in provenance['inputs_source_sha256'].items():assert sha(P/name)==digest
    report=read(static/'report.json');assert sha(static/'report.json')==provenance['report_sha256']
    original=read(D/'report.json');partial=[r for r in original['records'] if r['attempt']['outcome']=='partial_budget']
    rows={r['sha256']:r for r in report['records']}
    assert len(rows)==len(partial)==report['partial_count']==43
    counts=Counter();completed_inputs=0
    for r in partial:
        attempts=r['attempt']['stats']['attempts'];last=attempts[-1];s=rows[r['sha256']]
        assert (s['attempt_index'],s['attempt_count'],s['parent'],s['actual_processed_states'],s['actual_completed_outputs'],s['actual_message'])==(len(attempts)-1,len(attempts),last['parent'],last['processed_states'],last['complete_outputs'],last['message'])
        assert s['actual_completed_outputs']==0 and s['actual_frontier_ages'] is None
        assert sha(P/s['saved_baseline_path'])==s['saved_baseline_sha256']
        assert s['all_order_interleaving_count_upper_bound']==math.comb(sum(s['side_lengths']),s['side_lengths'][0])
        state='state budget' in last['message'];counts['state' if state else 'time']+=1
        if state:counts['first' if len(attempts)==1 else 'later']+=1
        completed_inputs+=r['attempt']['completed_output_files']>0
    assert counts==dict(state=42,time=1,first=41,later=1) and completed_inputs==1
    assert report['state_exhaustions']==42 and report['first_pair_state_exhaustions']==41 and report['zero_completed_outputs']==43
    planfolder=P/'experiments/r167-tree-pair-anytime-static';planproof=read(planfolder/'provenance.json')
    for name,digest in planproof['files_sha256'].items():assert sha(P/name)==digest
    planpath=P/'research/level-stage/tree-pair-anytime-plan.md';text=planpath.read_text(encoding='utf-8')
    required=['w=2','g(s) = P + i+j + C','h(s) = N-p-i-j','f>=U','500ms','20,000','16','immutable','reopen','8960','COPY乘法','族外','unfinished_expansion']
    assert all(token in text for token in required)
    old=read(ROOT/'outputs/stage2-root-tree-branch-context-gold.json');assert old['passed']
    docfolder=P/'experiments/r165-subtree-stage-report';doc=read(docfolder/'report-provenance.json')
    for name,digest in doc['files_sha256'].items():assert sha(P/name)==digest
    for extension in ('tex','pdf'):
        assert sha(docfolder/('project18-subtree-research.'+extension))==sha(P/'reports'/('project18-subtree-research.'+extension))
    assert doc['pages']==4
    # Mathematical review: safe lower bound counts every remaining original
    # row; positive transition1+COPY preserves consistency, complete costs
    # N+COPY give the same order as COPY. Weighted order never prunes.
    result=dict(passed=True,reviewed_unix=time.time(),static_report_sha256=sha(static/'report.json'),plan_sha256=sha(planpath),
        static_provenance_sha256=sha(static/'provenance.json'),plan_provenance_sha256=sha(planfolder/'provenance.json'),
        partial_inputs=43,state_exhaustions=42,first_pair_state_exhaustions=41,later_pair_state_exhaustions=1,time_exhaustions=1,
        last_failed_pair_complete_outputs=0,partial_inputs_with_earlier_complete_outputs=1,actual_unfinished_frontier_available=False,
        report_tex_sha256=sha(P/'reports/project18-subtree-research.tex'),report_freeze_sha256=sha(docfolder/'report-provenance.json'),
        root_builtin_compilation='actual success2026-10-11; no new tab, current user-open27 TeX untouched',
        proposal='Fixed w2 weighted visitation with safe unweighted full N+COPY bound, exact-role-state lower-cost reopen and immutable predecessors. Existing complete incumbent retained, emitted full suffix checked before lowering U; partial budget/outlet and unfinished expansion explicitly unknown.',
        authorized_next_scope='Implement isolated single search extension and verify unchanged R16340 original inputs/8960 independent frozen merge gold plus complete12 and budget/reopen/external-role boundaries before root review and original84. No default/full-corpus promotion yet.',
        scope='Frozen actual R164 counters independently attributed:42 state exhaustions,41 first-pair,one third-pair;43 last failing pairs have zero outlets but one input has earlier complete output. No missing historical age-frontier manufactured. Static full-cost admissibility and equal-state dominance reviewed; no COPY multiplicative approximation, first-goal or algorithm success claim.')
    (ROOT/'outputs/stage2-root-tree-pair-anytime-plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
