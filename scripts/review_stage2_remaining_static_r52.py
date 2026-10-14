"""Independent ID/set transitive envelopes for actual remaining original inputs."""
import hashlib
import json
import time
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/27-aicore-streams'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    rp=P/'reports/remaining-static-classification-batch52.json'
    report=json.loads(rp.read_text());bank=json.loads((P/'research/batch52/remaining63-input-only.json').read_text())['cases']
    for name,digest in report['sha256'].items():
        path=Path(name);assert sha(path if path.is_absolute() else P/path)==digest
    original=[]
    for ip,op in [('data/hard-corpus-resumed.json','reports/hard-functional-batch51.json'),('data/projection-retention-heldout-batch45.json','reports/heldout-functional-batch51.json')]:
        ins=json.loads((P/ip).read_text())['cases'];outs=json.loads((P/op).read_text())['cases']
        for case,row in zip(ins,outs):
            assert case['name']==row['name']
            if not row['pass']:
                original.append({k:case[k] for k in ('name','hardware','nodes','deadline_us','expected_feasible')})
    assert bank==original and len(bank)==len(report['cases'])==63
    upperfit,anylower,alllower,serialfits,producers=0,0,0,0,0
    for case,row in zip(bank,report['cases']):
        assert case['name']==row['name']
        nodes={n['id']:n for n in case['nodes']};parents={k:set(v['inputs']) for k,v in nodes.items()}
        assert len(nodes)==len(case['nodes']) and all(p in nodes for ps in parents.values() for p in ps)
        children={k:set() for k in nodes}
        for child,ps in parents.items():
            for parent in ps:children[parent].add(child)
        @lru_cache(None)
        def ancestors(k):
            return frozenset(parents[k].union(*(ancestors(p) for p in parents[k])))
        @lru_cache(None)
        def descendants(k):
            return frozenset(children[k].union(*(descendants(p) for p in children[k])))
        expected={r['producer_id']:r for r in row['release_cut_static']['producers']}
        uppers,lowers=[],[]
        for p in nodes:
            if not children[p] or nodes[p]['output_memory']==0:continue
            closure=set(children[p]).union(*(ancestors(user) for user in children[p]))-{p}-ancestors(p)
            forced=closure & descendants(p)
            r=expected.pop(p)
            assert len(closure)==r['initial_closure_upper'] and len(forced)==r['initial_closure_lower']
            assert r['output']==nodes[p]['output_memory'] and r['original_direct_users']==len(children[p])
            uppers.append(len(closure));lowers.append(len(forced));producers+=1
        assert not expected
        fit=bool(uppers) and max(uppers)<=128
        assert fit==row['release_cut_static']['initial_upper_all_fit']
        upperfit+=fit;anylower+=any(n>128 for n in lowers);alllower+=bool(lowers) and all(n>128 for n in lowers)
        serial=sum(n['exec_time'] for n in nodes.values())
        assert serial==row['serial_time'];serialfits+=serial<=case['deadline_us']
        assert len(nodes)<=4096
        digest=hashlib.sha256(json.dumps({k:case[k] for k in ('hardware','nodes','deadline_us')},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        assert digest==row['input_sha']
    assert (upperfit,anylower,alllower,serialfits)==(28,28,0,63)
    result=dict(passed=True,reviewed_unix=time.time(),original_input_records=63,eligible_producer_envelopes=producers,
        all_upper_closures_fit128_cases=upperfit,any_immediate_lower_over128_cases=anylower,all_immediate_lower_over128_cases=alllower,
        serial_deadline_satisfied_cases=serialfits,evidence={rp.relative_to(ROOT).as_posix():sha(rp)},
        scope='Root independent ID-set recursive ancestor/descendant envelopes agree with every eligible producer and original57+6 full unchanged inputs. At any completed-p prefix all p ancestors are done, so remaining DIRECT-user closure is a subset of this upper envelope:128 cap cannot explain28 cases. Immediate lower bound can shrink later; upper>128 is not actual rejection. No static result proves infeasibility, greedy cause, runtime budget or recovery; witness/generation excluded from candidate inputs.')
    (ROOT/'outputs/stage2-root-remaining-static-r52.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
