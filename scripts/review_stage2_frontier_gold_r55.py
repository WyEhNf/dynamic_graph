"""Audit actual compiler controls and original complete-cut physical plans."""
import json,time
from review_stage2_frontier_static_r55 import ROOT,P,sha,read

def main():
    d=P/'research/batch55'; m=read(d/'gold-completion.json');gold=read(d/'gold160.json')
    assert sha(d/'gold-completion.json')=='2921185392ae84de35956230193720283d4843e0b96a1b1840ac6885b9fc70d1'
    assert m['status']=='ACTUAL_TERMINAL_EXIT0_COMPILER160_GOLD_GATE' and not m['same12_solver_executed'] and not m['default_changed']
    assert m['preexecution_freeze_sha256']==sha(d/'pre-execution-freeze.json')
    for f in m['files']:assert sha(P/f['path'])==f['sha256']
    assert len(m['statuses'])==9 and all(x['actual_exit_code']==0 for x in m['statuses'])
    for status in m['statuses']:assert (P/status['stdout_path']).exists()and (P/status['stderr_path']).exists()
    expected={x['name']:x for x in gold['cases']};replayed=0;results=[]
    for compiler in ['gcc','ubsan']:
        path=P/f'reports/cut-repair-{compiler}-batch55.json'; r=read(path);assert r['count']==len(r['cases'])==160
        assert sha(path)=='fba2cf5d8ed3fb469b443ec180df862c84dc58a0295c1021e4801b20eefd8efd'
        assert {x['name']for x in r['cases']}==set(expected)
        for row in r['cases']:
            case=expected[row['name']];reference=case['expected']
            for key in ['valid','exhausted','work','peak','final_live','pending','order']:assert row[key]==reference[key]
            physical=row['fixed_physics'];assert physical['valid']==case['whole_physics']['valid']
            if physical['valid']:assert physical['T']==case['whole_physics']['T']and physical['peak']==case['whole_physics']['peak']
            nodes={v['id']:v for v in case['nodes']};consumers={i:set()for i in nodes}
            for v in nodes.values():
                for p in v['inputs']:consumers[p].add(v['id'])
            def live(done):return sum(nodes[i]['output_memory']for i in done if not consumers[i]or consumers[i]-done)
            def cut(actual):
                nonlocal replayed
                if not actual['valid']:return
                done=set(case['prefix']);peak=live(done)
                for i in actual['order']:
                    assert i not in done and set(nodes[i]['inputs'])<=done
                    overlap=live(done)+nodes[i]['workspace_memory']+nodes[i]['output_memory'];assert overlap<=case['hardware']['memory_limit']
                    peak=max(peak,overlap);done.add(i)
                assert not consumers[case['producer']]-done
                assert peak==actual['peak']and live(done)==actual['final_live'];replayed+=1
            cut(row)
            direct=row['direct_repair_check'];declared=case.get('direct_repair_check');assert (direct is None)==(declared is None)
            if direct:
                for key in ['valid','exhausted','work','peak','final_live','order']:assert direct[key]==declared['expected'][key]
                cut(direct)
        results.append(dict(compiler=compiler,normal_controls=160,direct_controls=16,fixed_physics=160,valid_normal=116,expected_budget_exhausted=12,legal_fixed=138))
    assert replayed==264
    source=sha(d/'solution.cpp');assert source==m['candidate_source_sha256']
    result=dict(passed=True,reviewed_unix=time.time(),completion_sha256=sha(d/'gold-completion.json'),source_sha256=source,actual_compiler_results=results,independent_actual_cut_physical_replays=replayed,actual_build_and_gate_exit_codes=[x['actual_exit_code']for x in m['statuses']],authorization='One same-originalR52twelve source-only GCC helper+whole batch, preserve all failures/logicalcost/completeplans. Root replay actualplans before broader decisions. No63/67/full/performance/default promotion.',scope='Root verifies true compiler/driver terminal logs/frozen source/gold and all320normal+32direct+320fixed observations.264actual validcut orders independently replayed against completeoriginal DAG/global DIRECTusers with bigint memory;12 exhausted percompiler remain unknown,22 invalid suppliedwholeplans retained percompiler. Same12 driver only compiled, no corpus recovery claimed yet.')
    (ROOT/'outputs/stage2-root-frontier-gold-r55.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
