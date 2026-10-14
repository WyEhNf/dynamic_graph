"""Root replay of complete original prefixes and all saved physical cut state."""
import json
import time
from collections import Counter
from review_stage2_release_cut_gold_r51 import ROOT,P,simulate,sha


def main():
    d=P/'research/batch52';reports=P/'reports'
    read=lambda path:json.loads(path.read_text())
    final=read(d/'observer-completion.json');assert final['actual_exit_code']==0 and final['actual_session']==35073
    for name,digest in final['files'].items():assert sha(P/name)==digest,name
    plan=read(d/'observer-plan.json');assert sha(d/'observer-plan.json')==final['plan_sha']
    assert sha(P/'solution/solution.cpp')==plan['default_source_sha']
    assert sha(P/'build/aicore_bench.exe')==plan['default_exe_sha']
    assert sha(P/'reports/project27-research.tex')==plan['old_tex_sha']
    original=(P/'research/batch51/solution.cpp').read_text()
    originalcut=(P/'research/batch51/release-cut.cpp.inc').read_text()
    observercut=(d/'observer-cut.cpp.inc').read_text()
    helper=(d/'observer.cpp.inc').read_text()
    roundtrip=read(d/'instrumentation-roundtrip.json');assert len(roundtrip['changes'])==14
    cut=observercut.replace(helper+'\n','',1)
    cut=cut.replace('{observe_probe_exit(h,g,r,frame,work,limit);return r;}','return r;')
    cut=cut.replace('{observe_outer_exit(h,g,r,frame,limit);return r;}','return r;')
    for change in reversed(roundtrip['changes']):
        assert cut.count(change['observation'])==change['count']
        cut=cut.replace(change['observation'],change['original'])
    assert cut==originalcut
    wrapper='''  auto cut=release_cut_order(h,g,std::min<I>(2000000,work_limit));
  if(cut.order.size()==static_cast<size_t>(g.n))return cut;
  auto original=projection_memory_search_r48(h,g,work_limit-cut.work);
  original.work+=cut.work;original.evaluations+=cut.evaluations;
  return original;'''
    wrapped='''  auto cut=release_cut_order(h,g,std::min<I>(2000000,work_limit));
  observer.cut_work=cut.work;observer.cut_exhausted=cut.exhausted;observer.cut_complete=cut.order.size()==static_cast<size_t>(g.n);
  if(cut.order.size()==static_cast<size_t>(g.n)){observer.total_work=cut.work;return cut;}
  auto original=projection_memory_search_r48(h,g,work_limit-cut.work);
  observer.projection_work=original.work;observer.projection_exhausted=original.exhausted;
  original.work+=cut.work;original.evaluations+=cut.evaluations;
  observer.total_work=original.work;return original;'''
    restored=(d/'observer-solution.cpp').read_text().removeprefix('#include <sstream>\n#include <string>\n')
    assert restored.count(wrapped)==restored.count(observercut)==1
    assert restored.replace(wrapped,wrapper,1).replace(observercut,originalcut,1)==original
    inputs=read(d/'observer-selected12-input-only.json')['cases']
    before=read(reports/'observer-baseline-batch52.json')['cases']
    after=read(reports/'observer-observed-batch52.json')['cases']
    default=read(reports/'observer-actual-default-batch52.json')['cases']
    assert len(inputs)==len(before)==len(after)==len(default)==12
    states=prefixes=full=0;causes=Counter();failedcauses=Counter();physical=[]
    metric_names={0:'candidates',1:'feasible_candidates',5:'duplicate_candidates',6:'attempts',7:'beam_expansions',8:'beam_width',9:'optimal_certificate',10:'time_lower_bound',11:'memory_lower_bound'}
    for case,a,b,c in zip(inputs,before,after,default):
        assert case['name']==a['name']==b['name']==c['name']
        assert not {'generation','witness_plan'} & case.keys()
        assert a['helper']==b['helper'] and a['whole']==b['whole']
        assert (b['whole']['valid'],b['whole']['T'],b['whole']['peak'],b['whole']['error'],b['whole']['plan'])==(c['valid'],c['T'],c['peak_memory'],c['error'],c['plan'])
        for k,name in metric_names.items():assert b['whole']['metrics'][str(k)]==c[name]
        nodes={n['id']:n for n in case['nodes']};ids=list(nodes);children={i:[] for i in nodes}
        for i,n in nodes.items():
            assert len(n['inputs'])==len(set(n['inputs']))
            for p in n['inputs']:children[p].append(i)
        cap=case['hardware']['memory_limit']
        def live(done):return sum(nodes[i]['output_memory'] for i in done if not children[i] or set(children[i])-done)
        def replay(order,initial=()):
            done=set(initial);peak=live(done)
            for i in order:
                assert i in nodes and i not in done and set(nodes[i]['inputs'])<=done
                allocation=live(done)+nodes[i]['workspace_memory']+nodes[i]['output_memory']
                assert allocation<=cap,(case['name'],i,allocation,cap)
                peak=max(peak,allocation);done.add(i)
            return done,live(done),peak
        for scope in ('helper_observer','whole_observer'):
            log=b[scope];assert log['cut_work']<=2000000 and log['total_work']<=16000000
            assert log['cut_work']+log['projection_work']==log['total_work']
            if scope=='helper_observer':assert log['total_work']==b['helper']['work']
            for state in log['snapshots']:
                states+=1;assert state['state_initialized'] and not state['transition_may_be_incomplete']
                assert state['node_ids']==ids and state['memory_limit']==cap
                assert state['charged_work']<=state['limit']<=2000000
                outerorder=state['outer_completed_order']
                # Successful R51 moves prefix into its returned order before
                # observing. The frame's moved-from vector is then empty.
                if state['kind']=='outer' and state['reason']=='complete_graph':
                    assert not outerorder and len(state['probe_completed_order'])==len(nodes)
                    outerorder=state['probe_completed_order']
                done0,initial,_=replay(outerorder);prefixes+=1
                if state['kind']=='probe':
                    assert state['initial_live']==initial
                    done,current,peak=replay(state['probe_completed_order'],done0);prefixes+=1
                else:
                    done,current=done0,initial;assert state['initial_live']==0
                    if scope=='helper_observer':
                        causes[state['reason']]+=1
                        if not b['whole']['valid']:failedcauses[state['reason']]+=1
                assert state['done']==[int(i in done) for i in ids]
                users=[len(set(children[i])-done) for i in ids]
                degree=[len(set(nodes[i]['inputs'])-done) for i in ids]
                assert state['remaining_direct_users']==users and state['remaining_degree']==degree
                assert state['live']==current==live(done)
                ready=[i for i in ids if i not in done and set(nodes[i]['inputs'])<=done]
                fit=[i for i in ready if current+nodes[i]['workspace_memory']+nodes[i]['output_memory']<=cap]
                assert state['global_ready_ids']==ready and state['global_ready_fit_ids']==fit
                seen=set(state['closure_construction_seen_ids'])
                assert seen<=set(ids) and not seen&done0
                assert state['cut_ready_ids']==[i for i in ready if i in seen]
                assert state['cut_ready_fit_ids']==[i for i in fit if i in seen]
                if state['kind']=='probe' and state['phase'] in ('greedy','apply','completion'):
                    producer=state['producer_id'];closure=set();stack=list(set(children[producer])-done0)
                    while stack:
                        i=stack.pop()
                        if i in done0 or i in closure:continue
                        closure.add(i);stack.extend(nodes[i]['inputs'])
                    assert seen==closure
                held=[];sink=external=0
                for i in ids:
                    if i not in done or not nodes[i]['output_memory'] or not (set(children[i])-done or not children[i]):continue
                    pending=[c for c in children[i] if c not in done]
                    outside=[c for c in pending if c not in seen] if state['kind']=='probe' and state['phase'] not in ('initial','copy') else []
                    held.append(dict(producer_id=i,output=nodes[i]['output_memory'],sink=not children[i],remaining_user_ids=pending,outside_cut_user_ids=outside))
                    if not children[i]:sink+=nodes[i]['output_memory']
                    if outside:external+=nodes[i]['output_memory']
                assert state['held_outputs']==held and state['held_sink_output']==sink and state['held_external_cut_output']==external
                if state['kind']=='outer' and state['reason']=='no_progress':assert ready and not fit
                if state['kind']=='outer' and state['reason']=='budget_exhausted':assert ready==fit and ready
        if b['whole']['valid']:
            assert simulate(case,b['whole']['plan'])==(b['whole']['T'],b['whole']['peak']);full+=1
        physical.append(dict(name=case['name'],helper_work=b['helper']['work'],whole_valid=b['whole']['valid']))
    assert states==138 and full==4 and causes=={'no_progress':8,'budget_exhausted':3,'complete_graph':1}
    assert failedcauses=={'no_progress':5,'budget_exhausted':3}
    gold=read(d/'whole-fixed-gold.json')['cases'];assert len(gold)==8
    valid=0
    for g in gold:
        wide=dict(g,hardware=dict(g['hardware']))
        wide['hardware']['memory_limit']=sum(n['output_memory']+n['workspace_memory'] for n in g['nodes'])
        T,peak=simulate(wide,g['fixed_plan']);ok=peak<=g['hardware']['memory_limit']
        assert (T,peak,ok)==(int(g['gold_T']),int(g['gold_peak']),g['gold_valid'])
        if ok:assert simulate(g,g['fixed_plan'])==(T,peak)
        valid+=ok
    assert valid==4
    result=dict(passed=True,reviewed_unix=time.time(),completion_sha256=sha(d/'observer-completion.json'),plan_sha256=sha(d/'observer-plan.json'),
        unchanged_default_exe_sha256=sha(P/'build/aicore_bench.exe'),source_roundtrip_insertions=14,original_cases=12,
        physical_snapshots=states,actual_original_prefix_replays=prefixes,full_recovery_plans=4,whole_bigint_gold=8,valid_gold=valid,
        all_cut_terminal_causes=dict(causes),failed_whole_case_terminal_causes=dict(failedcauses),case_evidence=physical,
        scope='Every saved coherent prefix replayed with original BEGIN/END memory, topology and exact done set; direct users/degree/global and cut ready-fit sets/held external and sink outputs checked. Pure observation round-trip and unchanged plans/work/default verified. Five no-fit and three budget exits are heuristic causes, not graph infeasibility or performance evidence.')
    (ROOT/'outputs/stage2-root-observer-r52.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='case_evidence'}))


if __name__=='__main__':main()
