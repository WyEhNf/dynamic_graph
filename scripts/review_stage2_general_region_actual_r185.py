"""Root full-output, symbolic/integer and physical-history label replay."""
import json,time
from collections import Counter
from review_stage2_general_region_source_r183 import ROOT,P,sha
from review_stage2_spine_extensions import replay,fingerprint,distance
D=P/'experiments/r185-general-region-functional'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def lines(p):return [json.loads(s)for s in p.read_text(encoding='utf-8').splitlines()]
def evaluate(rows,registers,bits=None,signed=False):
    registers=dict(registers);history=[]
    for row in rows:
        args=[history[-distance(t)]for t in row.get('inputs',[])]
        if row['op']=='GET':v=registers[row['reg']]
        elif row['op']=='SET':registers[row['reg']]=args[0];v=None
        elif row['op']=='COPY':v=history[-distance(row['source'])]
        elif bits is None:v=(row['op'],*args)
        else:
            v=(args[0]+args[1]if row['op']=='ADD'else args[0]*args[1])%(1<<bits)
            if signed and v>=1<<(bits-1):v-=1<<bits
        history.append(v)
    return registers
def main():
    m=read(D/'evidence-provenance.json');r=read(D/'report.json'); prepared=P/'experiments/r184-general-region-functional-prepared'
    assert sha(D/'report.json')=='c3fd2d274f756b14cdf26909e9718ee307adb385c4d437eafad03479b61e3d9b'
    assert m['source_manifest_sha256']==sha(prepared/'source-provenance.json')
    for name,digest in m['files_sha256'].items():assert sha(D/name)==digest
    cases=lines(prepared/'cases.jsonl'); assert len(cases)==len(r['records'])==81
    checked=labels_total=complete=improved=before=after=frontier_bytes=0;oracle_status=Counter()
    for case,row in zip(cases,r['records']):
        data=case['input'];key=fingerprint(data);assert row['sha256']==key and row['status']=='verified_initial_fallback'
        originals=data['instructions'];args=[[i-distance(t)for t in x.get('inputs',[])]for i,x in enumerate(originals)];users=[set()for _ in originals]
        for i,operands in enumerate(args):
            for p in operands:users[p].add(i)
        required=[set(x)for x in args];writers={};readers={}
        for i,original in enumerate(originals):
            if original['op'] not in ['GET','SET']:continue
            reg=original['reg']
            if reg in writers:required[i].add(writers[reg])
            if original['op']=='GET':readers.setdefault(reg,set()).add(i)
            else:required[i].update(readers.get(reg,set()));readers[reg]=set();writers[reg]=i
        names=sorted({x['reg']for x in originals if 'reg'in x});symbolic={n:('reg',n)for n in names}
        def check(saved):
            nonlocal checked
            cost=replay(data,dict(saved,input_sha256=key));assert cost==saved['copies']
            output=saved['output']['optimized_instructions'];assert evaluate(originals,symbolic)==evaluate(output,symbolic)
            for seed in [18501,18502]:
                for bits,signed in [(8,True),(16,False),(32,True)]:
                    initial={n:((seed-29*i)%(1<<bits))for i,n in enumerate(names)}
                    if signed: initial={n:(v-(1<<bits)if v>=1<<(bits-1)else v)for n,v in initial.items()}
                    assert evaluate(originals,initial,bits,signed)==evaluate(output,initial,bits,signed)
            checked+=1;return cost
        initial=read(D/(key[:16]+'-initial.json'));best=read(D/(key[:16]+'-best.json'));a=check(initial);b=check(best)
        assert a==row['before_copies'] and b==row['after_copies']<=a; before+=a;after+=b;improved+=b<a
        oracle=read(D/(key[:16]+'-oracle.json'));oracle_status[oracle['outcome']]+=1
        if oracle.get('output')is not None:
            check(dict(output=oracle['output'],original_order=oracle['original_order'],copies=oracle['copies']));assert oracle['copies']<=b
        saved=lines(D/(key[:16]+'-complete.jsonl'));assert len(saved)==row['actual_complete_outputs']
        for proposal in saved:
            check(proposal['candidate']);complete+=1
        for export in row['diagnostic_exports']:
            assert export['start']==0 # All81 small inputs fit the entire32-node region; no nonzero-prefix claim.
            path=P/export['path'];assert sha(path)==export['sha256'] and path.stat().st_size==export['bytes'];frontier_bytes+=export['bytes']
            records=lines(path);labels={}
            for record in records:
                if record['kind']=='header':continue
                if record['kind']=='immutable_label':labels[record['label_version']]=record;labels_total+=1
                v=record['label_version']; chain=[];visited=set()
                while labels[v]['predecessor_label']is not None:
                    assert v not in visited;visited.add(v);chain.append(labels[v]['action']);v=labels[v]['predecessor_label']
                chain.reverse();history=[];done=set();w=1<<data['bit_width']
                for i in chain:
                    assert i not in done and required[i]<=done
                    while len(history)>=w:
                        oldest=history[-w];last=oldest in args[i] and not(users[oldest]-(done|{i})) if oldest is not None else False
                        if oldest is None or not(users[oldest]-done)or last or oldest in history[-w+1:]:break
                        history.append(oldest)
                    assert all(p in history[-w:]for p in args[i]);history.append(None if originals[i]['op']=='SET'else i);done.add(i)
                roles=[]
                for i in done:
                    if users[i]-done:
                        age=len(history)-max(k for k,v in enumerate(history)if v==i);assert age<=w;roles.append([i,age])
                mask=sum(1<<initial['original_order'].index(i)for i in chain)
                assert record['done_mask']==mask and sorted(roles)==record['roles'] and record['g']==len(history)and record['h']==len(originals)-len(done)
        assert row['stats']['attempted_transitions']<=20000 and row['stats']['processed_states']<=20000
    assert (checked,labels_total,complete,improved,before,after)==(239,184,10,8,24,0)
    assert oracle_status==dict(optimal=67,unknown_discovery_budget=13,not_applicable_N11=1)
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(D/'report.json'),actual_exit_code=0,fixed_inputs=81,actual_search_inputs=8,initial_zero_COPY_inputs=73,whole_outputs_checked=checked,complete_proposals=complete,immutable_labels_physically_replayed=labels_total,frontier_bytes=frontier_bytes,before_COPY=before,after_COPY=after,improved_inputs=improved,oracle_statuses=dict(oracle_status),hand11_COPY_before=3,hand11_COPY_after=0,
        authorization='Prepare exact same336 R178-incumbent general-region refinement scope for all272legal and retain64nonlegal; freeze whole-corpus inputs/baselines/oldstatuses/resource/runner before execution. No default/official score claim.',
        scope='All81 outputs legal,239actual wholeoutputs physically/symbolically/sixinteger replayed and184immutable labels reconstructed from original physicalhistories. 73initialzeroCOPY inputs do not test search quality. All regions start0/fullsmallblock; no actual unfinished/negative/resourcehalt coverage in this batch beyond separate tencontracts. Oracle13unknown retained. hand11 actual3to0, not Level or full336 improvement.')
    (ROOT/'outputs/stage2-root-general-region-actual-r185.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
