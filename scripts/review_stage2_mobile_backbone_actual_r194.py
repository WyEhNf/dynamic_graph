"""Independent original-identity outputs and cursor physical-ring induction."""
import gzip,hashlib,json
from collections import Counter
from pathlib import Path
from review_stage2_spine_extensions import replay,fingerprint,distance
from review_stage2_general_region_actual_r185 import evaluate
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/18-isa-scheduler';PRE=P/'experiments/r193-mobile-backbone-prepared';D=P/'experiments/r194-mobile-backbone-small'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def gzlines(p):
    with gzip.open(p,'rb') as f:
        for line in f:yield line,json.loads(line)
class CursorRing:
    def __init__(self,data,initial,region):
        self.rows=data['instructions'];self.n=len(self.rows);self.w=1<<data['bit_width'];self.order=initial['original_order'];self.rank={i:k for k,i in enumerate(self.order)}
        self.L,self.R=region['L'],region['R'];self.members=region['mobile'];self.local={node:i for i,node in enumerate(self.members)};self.backbone=[i for i in self.order[self.L:self.R+1] if i not in self.local]
        self.args=[];self.deps=[];self.users=[set() for _ in self.rows];writes={};reads={}
        for i,row in enumerate(self.rows):
            operands=[i-distance(t) for t in row.get('inputs',[])];required=set(operands);self.args.append(operands)
            for j in operands:self.users[j].add(i)
            if row['op'] in ('GET','SET'):
                reg=row['reg']
                if reg in writes:required.add(writes[reg])
                if row['op']=='GET':reads.setdefault(reg,set()).add(i)
                else:required.update(reads.get(reg,set()));reads[reg]=set();writes[reg]=i
            self.deps.append(required)
        ring=[];cursor=g=0
        for row in initial['output']['optimized_instructions']:
            if row['op']!='COPY' and cursor==self.L:break
            if row['op']=='COPY':identity=ring[-distance(row['source'])]
            else:identity=None if row['op']=='SET' else self.order[cursor];cursor+=1
            ring=(ring+[identity])[-self.w:];g+=1
        assert cursor==self.L;self.seed=(0,0,tuple(ring),g);self.labels={}
    def completed(self,mask,cursor):return set(self.order[:self.L])|set(self.backbone[:cursor])|{i for i in self.members if mask&(1<<self.local[i])}
    def roles(self,done,ring):
        latest={node:index for index,node in enumerate(ring) if node is not None}
        return sorted([node,len(ring)-index] for node,index in latest.items() if self.users[node]-done)
    def step(self,parent,node):
        mask,cursor,ring,g=parent;done=self.completed(mask,cursor);assert node not in done and self.deps[node]<=done
        if node in self.local:newmask,newcursor=mask|(1<<self.local[node]),cursor
        else:assert cursor<len(self.backbone) and node==self.backbone[cursor];newmask,newcursor=mask,cursor+1
        ring=list(ring);rotations=0;nextdone=done|{node}
        while len(ring)==self.w:
            oldest=ring[0];last=oldest in self.args[node] and not(self.users[oldest]-nextdone) if oldest is not None else False
            if oldest is None or not(self.users[oldest]-done) or last or oldest in ring[1:]:break
            assert rotations<self.w;ring=ring[1:]+[oldest];g+=1;rotations+=1
        assert all(x in ring for x in self.args[node]);needed={x for x,_ in self.roles(done,ring) if self.users[x]-nextdone}
        if self.rows[node]['op']!='SET' and self.users[node]-nextdone:needed.add(node)
        ring=tuple((ring+[None if self.rows[node]['op']=='SET' else node])[-self.w:]);g+=1
        assert needed=={x for x,_ in self.roles(nextdone,ring)}
        return newmask,newcursor,ring,g
    def accept(self,r):
        if r['kind']=='header':
            assert r['region']==dict(L=self.L,R=self.R,mobile=self.members);return
        v=r['label_version']
        if r['kind']=='immutable_label':
            assert v not in self.labels;parent=r['predecessor_label']
            if parent is None:assert r['action'] is None;state=self.seed
            else:assert parent<v and parent in self.labels;state=self.step(self.labels[parent],r['action'])
            self.labels[v]=state
        else:assert r['kind'] in ('open','unfinished_expansion') and v in self.labels;state=self.labels[v]
        mask,cursor,ring,g=state
        assert mask==r['done_mask'] and cursor==r['backbone_cursor'] and g==r['g']
        assert r['h']==self.n-self.L-mask.bit_count()-cursor and r['roles']==self.roles(self.completed(mask,cursor),ring)
def main():
    report=read(D/'report.json');manifest=read(D/'evidence-provenance.json');assert manifest['source_manifest_SHA']==sha(PRE/'source-provenance.json')
    for name,digest in manifest['files'].items():assert sha(D/name)==digest,name
    cases=[json.loads(l) for l in (PRE/'cases.jsonl').read_text(encoding='utf-8').splitlines()];assert len(cases)==len(report['records'])==report['count']==84
    totals=Counter();frontier=Counter();outcomes=Counter();reference=Counter();details=[];regions=nonzero=0
    for case,row in zip(cases,report['records'],strict=True):
        data=case['input'];key=fingerprint(data);assert row['sha256']==key and row['kind']==case['kind'];initial=read(PRE/'initials'/f'{key}.json')
        names=sorted({r['reg'] for r in data['instructions'] if 'reg' in r});symbols={n:('reg',n) for n in names}
        def check(saved):
            cost=replay(data,dict(saved,input_sha256=key));assert cost==saved['copies'];rows=saved['output']['optimized_instructions']
            assert evaluate(data['instructions'],symbols)==evaluate(rows,symbols)
            for bits,signed in [(8,True),(16,False),(32,True)]:
                for seed in [19401,19402]:
                    values={n:(seed-29*i)%(1<<bits) for i,n in enumerate(names)}
                    if signed:values={n:(v-(1<<bits) if v>=1<<(bits-1) else v) for n,v in values.items()}
                    assert evaluate(data['instructions'],values,bits,signed)==evaluate(rows,values,bits,signed)
            totals['whole_outputs']+=1;return cost
        base=check(initial);assert base==row['before_copies'];totals['before_COPY']+=base
        if row['status']=='resource_unknown':assert row['after_copies']==base;totals['resource_unknown']+=1;totals['after_COPY']+=base;continue
        assert row['status']=='verified_initial_fallback';path=Path(row['complete_path']);assert path.drive.upper()=='G:' and sha(path)==row['compressed_complete_SHA']
        costs=[];decoded=0
        for blob,saved in gzlines(path):
            decoded+=len(blob);assert saved['input_sha256']==key
            region=saved['region'] if isinstance(saved['region'],dict) else row['stats']['attempts'][saved['region']]['region']
            beforeorder=initial['original_order'];afterorder=saved['candidate']['original_order'];L,R=region['L'],region['R'];mobile=set(region['mobile'])
            assert afterorder[:L]==beforeorder[:L] and afterorder[R+1:]==beforeorder[R+1:]
            assert set(afterorder[L:R+1])==set(beforeorder[L:R+1])
            assert [i for i in afterorder[L:R+1] if i not in mobile]==[i for i in beforeorder[L:R+1] if i not in mobile]
            costs.append(check(saved['candidate']));totals['proposals']+=1
        assert len(costs)==row['actual_complete_outputs'] and decoded==row['decoded_complete_bytes']
        best=next(gzlines(row['best_path']))[1];assert sha(row['best_path'])==row['best_compressed_SHA'];after=check(best)
        assert after==row['after_copies']==min([base]+costs);totals['after_COPY']+=after;totals['improved']+=after<base
        ref=read(D/f'{key[:16]}-reference.json');assert ref['outcome']==row['reference_outcome'];reference[ref['outcome']]+=1
        if ref.get('candidate') is not None:
            refcost=check(ref['candidate']);assert ref['outcome']=='optimal_neighborhood' and refcost<=after
            if case.get('old_gold_outcome')=='optimal':assert refcost==case['old_gold_copies']
        stats=row['stats'];outcomes[stats['outcome']]+=1;assert stats['processed_states']<=20000 and stats['attempted_transitions']<=20000
        totals['processed']+=stats['processed_states'];totals['attempted']+=stats['attempted_transitions']
        for e in row['diagnostic_exports']:
            path=Path(e['absolute_path']);assert path.drive.upper()=='G:' and sha(path)==e['compressed_SHA'];digest=hashlib.sha256();counts=Counter();decoded=0;ring=None
            for blob,r in gzlines(path):
                decoded+=len(blob);digest.update(blob);counts[r['kind']]+=1
                if r['kind']=='header':assert ring is None;ring=CursorRing(data,initial,r['region']);regions+=1;nonzero+=r['region']['L']>0
                assert ring is not None;ring.accept(r)
            assert dict(counts)==e['counts'] and decoded==e['decoded_bytes'] and digest.hexdigest()==e['decoded_SHA'];frontier.update(counts)
        details.append(dict(kind=case['kind'],input_sha256=key,before=base,after=after,proposals=len(costs),outcome=stats['outcome']))
        print(json.dumps(dict(kind=case['kind'],input=key[:16],whole=totals['whole_outputs'],labels=frontier['immutable_label'])),flush=True)
    contracts=Path('G:/Hackathon-stage2-artifacts/project18/r194-mobile-backbone-contracts/owner.log').read_text();assert 'Ran 15 tests' in contracts and contracts.rstrip().endswith('OK')
    result=dict(passed=True,report_sha256=sha(D/'report.json'),actual_tool_chunk='6337d3',actual_terminal_exit_code=0,contracts_passed=15,inputs=84,totals=dict(totals),frontier=dict(frontier),regions=regions,nonzero_prefix_regions=nonzero,reference=dict(reference),search_outcomes=dict(outcomes),extra_cases=[r for r in details if r['kind']!='frozen_tiny80'],scope='Root original identities, ordered operands, RAW/WAR/WAW, physical COPY, symbolic/sixinteger outputs and every immutable/OPEN/unfinished mobile mask+backbone cursor reconstructed independently. Each whole proposal preserves fixed prefix/suffix and backbone order, and uses the same initial. Isolated84 finite functionality does not prove official Level1-3 or full336 gains; all missing old64 remain unchanged.')
    (ROOT/'outputs/stage2-root-mobile-backbone-actual-r194.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
