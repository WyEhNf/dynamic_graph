"""Independent original-graph replay of recorded prefixes and necessary overlaps."""
import hashlib,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'projects/27-aicore-streams'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def main():
    d=P/'research/batch56'; report=read(d/'external-release-static.json')
    assert sha(d/'external-release-static.json')=='95ce1c438e08ec26f4110f2d6c296eb322d625fa0c1b8ef33d857841454b9bbe'
    for r in report['sources']: assert sha(P/r['path'])==r['sha256']
    checkpoint=read(P/'research/batch55/negative-checkpoint.json')
    for r in checkpoint['files']: assert sha(P/r['path'])==r['sha256'] and (P/r['path']).stat().st_size==r['bytes']
    cases=read(P/'research/batch52/observer-selected12-input-only.json')['cases']
    obs={c['name']:c for c in read(P/'reports/observer-observed-batch52.json')['cases']}
    originals={c['name']:c for f in ['hard-corpus-resumed.json','projection-retention-heldout-batch45.json'] for c in read(P/'data'/f)['cases']}
    proofs=[]; probe_count=0; replayed_rows=0
    for case,row in zip(cases,report['rows']):
        assert case['name']==row['name']; by={v['id']:v for v in case['nodes']}; users={i:set() for i in by}
        for i,v in by.items():
            for p in v['inputs']: users[p].add(i)
        cap=case['hardware']['memory_limit']
        def reach(start,forward=True):
            seen=set(); stack=list(users[start] if forward else by[start]['inputs'])
            while stack:
                i=stack.pop()
                if i in seen: continue
                seen.add(i); stack.extend(users[i] if forward else by[i]['inputs'])
            return seen
        ancestors={i:reach(i,False) for i in by}; descendants={i:reach(i)|{i} for i in by}
        def held(done): return {i for i in done if not users[i] or users[i]-done}
        def live(done): return sum(by[i]['output_memory'] for i in held(done))
        def fit(done,i): return i not in done and set(by[i]['inputs'])<=done and live(done)+by[i]['workspace_memory']+by[i]['output_memory']<=cap
        pins={j:[i for i in by if i!=j and by[i]['output_memory'] and (not users[i] or users[i]&descendants[j])] for j in by}
        def violations(done):
            result=[]
            for j in by:
                if j in done: continue
                must=done|ancestors[j]
                pinned=[i for i in pins[j] if i in must]
                bound=sum(by[i]['output_memory'] for i in pinned)+by[j]['workspace_memory']+by[j]['output_memory']
                if bound>cap: result.append(dict(node=j,bound=bound,held=pinned))
            return result
        snapshots=obs[case['name']]['helper_observer']['snapshots']; outer=next(s for s in snapshots if s['kind']=='outer')
        done=set();first=None
        prefix=outer['outer_completed_order']
        if outer['reason']=='complete_graph':
            assert not prefix
            prefix=outer['probe_completed_order'] # R51 moved the completed vector into its return value.
        for k,i in enumerate(prefix):
            assert fit(done,i); old=violations(done); done.add(i);new=violations(done);replayed_rows+=1
            if not old and new and first is None: first=dict(step=k,choice=i,bad=new)
        assert first==row['prefix_first_forced_overlap'] and violations(done)==row['terminal_forced_violations']
        assert done=={i for i,v in zip(outer['node_ids'],outer['done']) if v}
        assert live(done)==row['end_live']
        for pr in row['probes']:
            s=snapshots[pr['snapshot']]; D={i for i,v in zip(s['node_ids'],s['done']) if v}; C=set(s['closure_construction_seen_ids'])
            outside=[i for i in by if i not in C and fit(D,i)]
            assert len(outside)==pr['global_outside_fit']
            opens=[(i,j) for i in outside for j in C-D if fit(D|{i},j)]
            assert not opens and not pr['one_external_step_opens_cut']; probe_count+=1
        original=originals[case['name']]
        for key in ['nodes','hardware','deadline_us']: assert original[key]==case[key]
        stream=[s for s in original['witness_plan']['streams'] if s['tasks']]; assert len(stream)==1
        order=[t['op_id'] for t in stream[0]['tasks']]; assert len(order)==len(set(order))==len(by)
        D=set();peak=elapsed=0
        for i in order:
            assert fit(D,i); peak=max(peak,live(D)+by[i]['workspace_memory']+by[i]['output_memory']); elapsed+=by[i]['exec_time'];D.add(i)
        assert peak==row['diagnostic_witness_only']['peak'] and elapsed==row['diagnostic_witness_only']['T']<=case['deadline_us']
        if first and not row['whole_valid']:
            for failure in first['bad']:
                j=failure['node'];p=first['choice']; assert order.index(j)<order.index(p)
                closure=next(c for c in row['terminal_closure_coverage'] if c['producer']==p)
                assert closure['within128'] and closure['within_top24']
                proofs.append(dict(name=case['name'],step=first['step'],producer=p,blocked_original=j,necessary_bound=failure['bound'],memory_cap=cap,producer_rank=closure['rank'],closure_size=closure['size'],diagnostic_only_witness_j_before_p=True))
    assert len(proofs)==2 and probe_count==22
    result=dict(passed=True,reviewed_unix=time.time(),static_report_sha256=sha(d/'external-release-static.json'),negative_frozen_files=len(checkpoint['files']),original_inputs=12,prefix_rows_replayed=replayed_rows,probes=probe_count,one_outside_step_assists=0,strict_irreversible_prefix_proofs=proofs,original_witnesses_replayed=12,
        authorization='Review frozen input-only causal producer-deferral/restart design and full original small counterexamples before implementation. No solver/compile/63-input expansion or default promotion.',
        scope='Original recorded prefixes, original direct-user lifetimes and workspace+output BEGIN arithmetic independently replayed. Two failed prefixes cannot complete under unchanged memory cap; zero one-step assists in only22 recorded probes. Other failures remain unresolved. Diagnostic serial witnesses are never solver input; no new recovery/performance claim.')
    (ROOT/'outputs/stage2-root-causal-attribution-r56.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result))
if __name__=='__main__':main()
