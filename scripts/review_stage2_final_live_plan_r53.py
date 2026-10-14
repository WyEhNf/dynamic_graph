"""Root frozen-plan review and independent original-set manual arithmetic."""
import itertools
import json
import time
from collections import Counter
from review_stage2_observer_r52 import ROOT,P,sha


def main():
    d=P/'research/batch53';read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    freeze=read(d/'static-freeze.json');gold=read(d/'gold-declaration.json')
    assert freeze['status']=='STATIC_ONLY_NO_CPU_EXPERIMENT' and freeze['planned_controls']==gold['planned_controls']==176
    assert sum(gold['planned_control_counts'].values())==176 and gold['minimum_controls']==160
    assert freeze['budgets']==dict(cut=2000000,total=16000000,closure_nodes=128,held_top=24,seed_or_threshold_change=False,all_new_work_charged=True)
    for row in freeze['files']:
        path=P/row['path'];assert path.stat().st_size==row['size_bytes'] and sha(path)==row['sha256']
    assert len(freeze['files'])==13
    assert not any(freeze[k] for k in ('candidate_source_created','gold_executed','solver_executed','compile_executed','performance_executed','default_changed','old_open_tex_changed'))
    root=read(ROOT/'outputs/stage2-root-observer-r52.json');assert root['passed']
    templates=gold['manual_templates'];assert len(templates)==4
    bases={t['name']:t for t in templates};controls=[];orders=0
    for template in templates:
        base=bases[template['base_template']] if 'base_template' in template else template
        nodes={n['id']:dict(n) for n in base['nodes']}
        for key,value in template.get('workspace_overrides',{}).items():nodes[int(key)]['W']=value
        children={i:set() for i in nodes}
        for i,n in nodes.items():
            for p in n['inputs']:children[p].add(i)
        cap=template['capacity'];done=set();peak=0
        def held(completed):return sum(n['O'] for i,n in nodes.items() if i in completed and (not children[i] or children[i]-completed))
        def execute(order,initial):
            completed=set(initial);p=held(completed)
            for i in order:
                assert i not in completed and set(nodes[i]['inputs'])<=completed
                p=max(p,held(completed)+nodes[i]['W']+nodes[i]['O']);completed.add(i)
            return p,held(completed)
        prefix=template.get('prefix',base['prefix'])
        prefixpeak,_=execute(prefix,set());assert prefixpeak<=cap;done=set(prefix)
        producers=template.get('candidate_producers',base.get('candidate_producers',[template.get('producer')]))
        values=[];peaks=[];legal=[]
        for producer in producers:
            assert producer in done and children[producer]-done
            closure=set();stack=list(children[producer]-done)
            while stack:
                i=stack.pop()
                if i in done or i in closure:continue
                closure.add(i);stack.extend(nodes[i]['inputs'])
            union=done|closure;whole=held(union)
            release=sum(nodes[i]['O'] for i in done if children[i] and children[i]-done and children[i]-done<=closure)
            born=sum(nodes[i]['O'] for i in closure if not children[i] or children[i]-union)
            assert whole==held(done)-release+born
            feasible=[]
            for order in itertools.permutations(sorted(closure)):
                completed=set(done)
                if any(not set(nodes[i]['inputs'])<=completed or completed.add(i) for i in order):continue
                peak,actualfinal=execute(order,done);orders+=1;assert actualfinal==whole
                if peak<=cap:feasible.append(peak)
            values.append(whole);peaks.append(min(feasible) if feasible else None);legal.append(bool(feasible))
        if 'hand_final_values' in base:assert values==base['hand_final_values']
        if 'hand_final' in template:assert values==[template['hand_final']]
        if 'hand_candidate_peaks' in template:assert peaks==template['hand_candidate_peaks']
        if 'full_plan' in template:assert execute(template['full_plan'],set())[0]<=cap
        if template['name']=='three_competing_legal_cuts':assert values==[120,80,120] and all(legal)
        if template['name']=='dominated_cut_invalid_at_prefix_but_whole_graph_feasible':assert legal==[False,True,False]
        if template['name']=='equal_final_better_peak':assert values==[40,40] and peaks==[130,90]
        controls.append(dict(name=template['name'],final_live=values,minimum_legal_cut_peak=peaks,legal=legal))
    result=dict(passed=True,reviewed_unix=time.time(),static_freeze_sha256=sha(d/'static-freeze.json'),gold_declaration_sha256=sha(d/'gold-declaration.json'),
        manual_original_templates=4,manual_topological_cut_orders_replayed=orders,manual_controls=controls,predeclared_controls=176,
        complete176controls_executed=False,candidate_compiled=False,default_changed=False,
        design='Exact H(D union C) is order-independent before terminal sink clear. Distinct original-D parent release plus C external/sink born outputs agrees on manual original DAGs. Strictly larger F than a current actually legal incumbent can never improve (F,peak); equal must remain. All extra work charged, so finite-budget results require regression validation.',
        authorized_next_scope='Isolated single final-live filter, frozen charged-operation table and176 full-original controls; R52same12 functional cases after gold. No remaining63/full250/performance/default until actual small acceptance reviewed.',
        scope='Frozen13 references and unchanged R51/old user-open TeX verified. Four manual original templates independently replayed, including invalid cuts inside feasible whole graph, equal F better peak and external held output. This accepts design/next small verification, not all176 safety tests, new recovery, universal feasibility or speedup.')
    (ROOT/'outputs/stage2-root-final-live-plan-r53.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
