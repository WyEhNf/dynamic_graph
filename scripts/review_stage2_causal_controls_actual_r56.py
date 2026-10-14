"""Independent frozen-output audit with original-DAG bigint BEGIN/END memory."""
import hashlib,json
from collections import Counter
from pathlib import Path
from review_stage2_causal_reference_gold_r56 import physics,model
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/27-aicore-streams';D=P/'research/batch56';G=Path('G:/Hackathon-project27-owned/batch56-3a4f184d')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    frozen=read(D/'controls-completion-freeze-revision1.json')
    assert sha(D/'controls-completion-freeze-revision1.json')=='24a61498677b9d130c1f3df7e93951fb47f613ede32225b26698d59165edb19c'
    assert frozen['status']=='ACTUAL_TERMINAL_EXIT0_REVISION1_GCC_CLANG_CONTROLS_GATE' and not frozen['same12_solver_executed']
    for r in frozen['files']:
        p=Path(r['path']);p=p if p.is_absolute() else P/p;assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
    for name in ('compiler-controls-plan-freeze.json','compiler-controls-plan-freeze-revision1.json'):
        for r in read(D/name)['files']:
            p=Path(r['path']);p=p if p.is_absolute() else P/p;assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
    assert len(frozen['statuses'])==13 and all(r['actual_exit_code']==0 for r in frozen['statuses'])
    assert len(frozen['preflights'])==14
    for r in frozen['preflights']:
        p=P/r['raw_path'];assert sha(p)==r['raw_sha256'];raw=read(p)
        assert raw['passed'] and all(raw['checks'].values()) and raw['GlobalMemoryStatusEx']['structure_bytes']==64
        assert raw['GlobalMemoryStatusEx']['fields']['ullAvailPhys']>=1073741824 and raw['G_disk_usage']['free']>=1073741824 and raw['F_disk_usage']['free']>=67108864
    gold={c['name']:c for c in read(D/'gold160.json')['cases']};extras=read(D/'caller-guard-controls16.json');extra={c['name']:c for c in extras['cases']};summaries=[];physical_count=0
    for compiler in ('gcc','ubsan'):
        normal=read(G/'outputs'/('gold-'+compiler+'.json'));caller=read(G/'outputs'/('caller-'+compiler+'.json'))
        assert normal['count']==len(normal['cases'])==160 and caller['count']==len(caller['cases'])==16
        assert {c['name'] for c in normal['cases']}==set(gold) and {c['name'] for c in caller['cases']}==set(extra)
        counts=Counter()
        for c in normal['cases']:
            e=gold[c['name']]
            for k in ('producer','target','complete','exhausted','work'):assert c[k]==e['expected'][k],(compiler,c['name'],k)
            events,best,_=model(e['nodes'],e['prefix'],e['hardware']['memory_limit']);required=sum(fee for _,fee in events)
            assert c['work']==min(required,e['limit'])
            fixed=physics(e['nodes'],e['supplied_whole_order'],e['hardware']['memory_limit'],True);physical_count+=1
            assert c['fixed_physics']['valid']==fixed['valid']
            if fixed['valid']:assert (c['fixed_physics']['T'],c['fixed_physics']['peak'])==(fixed['T'],fixed['peak']);counts['fixed_legal']+=1
            else:counts['fixed_invalid']+=1
            assert 0<=c['whole_work']<=16000000
            if len(c['whole_order'])==len(e['nodes']):
                actual=physics(e['nodes'],c['whole_order'],e['hardware']['memory_limit'],True);physical_count+=1
                assert actual['valid'] and c['whole_physics']==dict(valid=True,T=actual['T'],peak=actual['peak']) and actual['T']<=e['deadline_us'];counts['helper_whole_legal']+=1
            else:assert not c['whole_physics']['valid'];counts['helper_whole_missing']+=1
            counts['qualified_pairs']+=c['producer'] is not None;counts['detector_exhausted']+=c['exhausted']
        for c in caller['cases']:
            e=extra[c['name']];f=extras['fixtures'][e['fixture']]
            for k,v in e['expected'].items():
                if k!='T':assert c[k]==v,(compiler,c['name'],k)
            p=physics(f['nodes'],f['fixed_order'],f['hardware']['memory_limit'],True);physical_count+=1
            assert c['fixed_physics']==dict(valid=True,T=p['T'],peak=p['peak'])
            if c['valid']:
                p=physics(f['nodes'],c['returned_whole_ids'],f['hardware']['memory_limit'],True);physical_count+=1
                assert p['valid'] and c['returned_physics']==dict(valid=True,T=p['T'],peak=p['peak']);counts['caller_valid']+=1
            else:assert c['returned_whole_ids']==[] and not c['returned_physics']['valid'];counts['caller_exhausted']+=1
        assert dict(counts)==dict(fixed_legal=144,fixed_invalid=16,helper_whole_legal=136,helper_whole_missing=24,qualified_pairs=96,detector_exhausted=12,caller_valid=5,caller_exhausted=11)
        summaries.append(dict(compiler=compiler,**dict(counts)))
    assert physical_count==634
    doc=dict(passed=True,actual_owner_session=97407,actual_terminal_exit_code=0,completion_freeze_sha256=sha(D/'controls-completion-freeze-revision1.json'),root_static_caller_review_sha256=sha(ROOT/'outputs/stage2-root-causal-caller-controls-r56.json'),compiler_summaries=summaries,independent_original_physics_replays=physical_count,actual_commands=13,fresh_resource_gates=14,frozen_completion_files=len(frozen['files']),source_sha256=sha(D/'solution.cpp'),scope='GCC and Clang UBSan actual160 detector/16 caller fee boundaries each, original bigint full-plan physical replay. Artificial helper136/160 complete each;24missing retained. No original12/63 recovery, performance or default promotion evidence.')
    (ROOT/'outputs/stage2-root-causal-controls-actual-r56.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps(doc))
if __name__=='__main__':main()
