"""Original-DAG bigint qualification and physical gold audit before C++ execution."""
import json,time,difflib
from collections import Counter
from review_stage2_frontier_static_r55 import ROOT,P,sha,read

def main():
    d=P/'research/batch55'; m=read(d/'pre-execution-freeze.json')
    assert sha(d/'pre-execution-freeze.json')=='8b6666017efd81ce5486f59f1abf8ea3c59f85c30f62e582569afb389289c412'
    for f in m['files']:assert sha(P/f['path'])==f['sha256']and (P/f['path']).stat().st_size==f['bytes']
    assert len(m['files'])==45 and not m['candidate_executed']and not m['default_changed']and not m['old_open_tex_changed']and not m['live_handles']
    source=(d/'solution.cpp').read_text(); original=(P/'solution/solution.cpp').read_text(); fragment=(d/'repair.cpp.inc').read_text()
    assert fragment in source and sha(d/'solution.cpp')==m['candidate_source_sha256']=='c17c1f67792a3aa8ffeeb60034c92ac7e7b48e0f0835bfd3c7e0e8f63f1a36ec'
    diff=list(difflib.unified_diff(original.splitlines(),source.splitlines()));assert sum(x.startswith('@@')for x in diff)==2
    assert fragment.index('if(!charge(1))return r;')<fragment.index('const int count=')<fragment.index('if(!count || count>128)return r;')
    call=source.index('auto repair=failed_cut_beam_repair(');assert source.index('if(!charge(2))return r;',call)<source.index('if(repair.valid)return repair;',call)
    gold=read(d/'gold160.json'); requests=read(d/'gold-driver-input.json'); assert gold['count']==len(gold['cases'])==len(requests['cases'])==160
    assert not gold['candidate_executed']and Counter(x['family']for x in gold['cases'])==dict(A=48,B=32,C=32,D=16,E=16,F=16)
    legal_whole=valid_cut=eligible=within128=direct=0; closure_sizes=Counter(); int64max=2**63-1
    for case,request in zip(gold['cases'],requests['cases']):
        assert all(case[k]==request[k]for k in ['name','hardware','nodes','prefix','producer','limit','supplied_whole_order'])
        nodes={v['id']:v for v in case['nodes']}; users={i:set()for i in nodes}
        for v in nodes.values():
            for key in ['workspace_memory','output_memory','exec_time']:assert 0<=v[key]<=int64max
            assert len(set(v['inputs']))==len(v['inputs'])
            for p in v['inputs']:users[p].add(v['id'])
        cap=case['hardware']['memory_limit']
        def held(D):return {i for i in D if not users[i]or users[i]-D}
        def live(D):return sum(nodes[i]['output_memory']for i in held(D))
        def physical(order,initial=()):
            done=set(initial);peak=live(done);valid=True;t=0
            for i in order:
                assert i not in done and set(nodes[i]['inputs'])<=done
                overlap=live(done)+nodes[i]['workspace_memory']+nodes[i]['output_memory'];peak=max(peak,overlap);valid &= overlap<=cap
                done.add(i);t+=nodes[i]['exec_time']
            return valid,peak,t,done
        pv,pp,pt,D=physical(case['prefix']);assert pv and case['qualifier']['prefix_physical_valid']and case['qualifier']['prefix_is_original_ideal']
        p=case['producer']; remaining=users[p]-D; stack=list(remaining); C=set()
        while stack:
            i=stack.pop()
            if i in D or i in C:continue
            C.add(i);stack.extend(nodes[i]['inputs'])
        q=case['qualifier']; assert q['producer_completed']==(p in D)and q['producer_positive_output']==bool(nodes[p]['output_memory'])
        assert set(q['remaining_original_DIRECT_users'])==remaining and set(q['closure_original_ids'])==C
        ok=p in D and bool(nodes[p]['output_memory'])and bool(remaining);assert q['eligible']==ok and q['within128']==(len(C)<=128)
        eligible+=ok;within128+=ok and len(C)<=128;closure_sizes[len(C)]+=1
        wv,wp,wt,whole=physical(case['supplied_whole_order']); assert whole==set(nodes)
        stored=case['whole_physics'];assert (wv,wp,wt)==(stored['valid'],stored['peak'],stored['T']);legal_whole+=wv
        expected=case['expected'];assert expected['work']<=case['limit']
        if expected['valid']:
            cv,cp,ct,end=physical(expected['order'],D);assert cv and set(expected['order'])==C and not users[p]-end
            assert cp==expected['peak']and live(end)==expected['final_live'];valid_cut+=1
        if len(C)>128:assert not expected['valid']and wv
        req=request['direct_repair_check']
        if req is not None:direct+=1;assert ok and len(C)<=128 and set(req['pending'])==C
    assert (eligible,within128,valid_cut,legal_whole,direct)==(158,150,116,138,16)
    literal=read(d/'literal-charge-gold.json'); fees=read(d/'charged-work-implementation.json'); assert len(fees['rows'])==35
    for template in literal['templates']:
        assert (template['setup'],template['first_valid_child'],template['complete_repair'])==(80,112,180)
        assert template['limits']==[0,79,80,111,112,179,180,181]
        work=0
        for event in template['events']:
            assert event['paid']and event['work_before']==work;work+=event['amount'];assert event['work_after']==work
        assert work==180
    assert fees['manual_whole_probe_trace']['old_greedy_until_nofit']==40
    assert sum([40,1,39,57,30,11,2])==180
    plan=read(d/'compiler-resource-plan.json');assert plan['minimum_F_free_bytes']==1073741824 and not plan['execution_started']
    result=dict(passed=True,reviewed_unix=time.time(),freeze_sha256=sha(d/'pre-execution-freeze.json'),frozen_files=45,candidate_source_sha256=m['candidate_source_sha256'],gold_controls=160,qualified_eligible=eligible,eligible_within128=within128,reference_valid_cuts=valid_cut,reference_legal_whole_orders=legal_whole,direct_only_controls=direct,closure_sizes=dict(closure_sizes),literal_boundaries=[80,112,180],authorization='Compile frozen GCC gold/selected12/standalone and Clang UBSan gold with F temp/min1GiB. First execute160normal+16direct+160fixedphysics controls per compiler; independently review before sameR52twelve source-only. No full63/67/250/performance/default promotion.',scope='Root all45source/gold/input hashes/two diff hunks reviewed. Independent bigint original-prefix and fullDIRECT unfinished closure qualification/all160 wholefixed orders/116legalcut outputs verified, including129/130 skips and largeint64 cases. Expanded35logical fee rows and hand80/112/180 transcript accepted before execution. These are pre-execution reference controls, not candidate passes/recoveries.')
    (ROOT/'outputs/stage2-root-frontier-implementation-r55.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
