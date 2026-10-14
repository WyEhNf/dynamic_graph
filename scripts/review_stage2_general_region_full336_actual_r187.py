"""Root original-identity whole-output and independent physical-ring induction."""
import gzip,hashlib,json,time
from collections import Counter
from pathlib import Path
from review_stage2_spine_extensions import replay,fingerprint,distance
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/18-isa-scheduler';D=P/'experiments/r187-general-region-full336';PREP=P/'experiments/r186-general-region-full336-prepared'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for b in iter(lambda:stream.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def lines(p):
    with gzip.open(p,'rt',encoding='utf-8') as stream:
        for line in stream:yield json.loads(line)
class Ring:
    def __init__(self,data,initial,start):
        self.original=data['instructions'];self.n=len(self.original);self.w=1<<data['bit_width'];self.start=start
        self.order=initial['original_order'];self.rank={i:k for k,i in enumerate(self.order)};self.members=self.order[start:start+32];self.local={i:k for k,i in enumerate(self.members)}
        self.args=[];self.deps=[];users=[set() for _ in range(self.n)];writers={};readers={}
        for i,row in enumerate(self.original):
            arg=[i-distance(t) for t in row.get('inputs',[])];self.args.append(arg);dep=set(arg)
            for p in arg:users[p].add(i)
            if row['op'] in ('GET','SET'):
                reg=row['reg']
                if reg in writers:dep.add(writers[reg])
                if row['op']=='GET':readers.setdefault(reg,set()).add(i)
                else:dep.update(readers.get(reg,set()));readers[reg]=set();writers[reg]=i
            self.deps.append(dep)
        self.masks=[sum(1<<self.local[c] for c in consumers if c in self.local) for consumers in users]
        self.suffix=[any(self.rank[c]>=start+len(self.members) for c in consumers) for consumers in users]
        ring=[];cursor=0;g=0
        for row in initial['output']['optimized_instructions']:
            if row['op']!='COPY' and cursor==start:break
            if row['op']=='COPY':identity=ring[-distance(row['source'])]
            else:
                i=self.order[cursor];cursor+=1;identity=None if row['op']=='SET' else i
            ring=(ring+[identity])[-self.w:];g+=1
        assert cursor==start;self.seed=(0,tuple(ring),g);self.labels={}
    def needed(self,i,mask):return self.suffix[i] or bool(self.masks[i]&~mask)
    def done(self,i,mask):return self.rank[i]<self.start or (i in self.local and bool(mask&(1<<self.local[i])))
    def roles(self,mask,ring):
        latest={v:k for k,v in enumerate(ring) if v is not None}
        return sorted([i,len(ring)-k] for i,k in latest.items() if self.needed(i,mask))
    def step(self,parent,i):
        mask,ring,g=parent;assert i in self.local and not self.done(i,mask) and all(self.done(p,mask) for p in self.deps[i])
        new=mask|(1<<self.local[i]);ring=list(ring);rotations=0;last={p for p in self.args[i] if not self.needed(p,new)}
        while len(ring)==self.w:
            oldest=ring[0]
            if oldest is None or not self.needed(oldest,mask) or oldest in last or oldest in ring[1:]:break
            assert rotations<self.w;ring=ring[1:]+[oldest];g+=1;rotations+=1
        assert all(p in ring for p in self.args[i])
        wanted={p for p,age in self.roles(mask,ring) if self.needed(p,new)}
        if self.original[i]['op']!='SET' and self.needed(i,new):wanted.add(i)
        ring=tuple((ring+[None if self.original[i]['op']=='SET' else i])[-self.w:]);g+=1
        assert wanted=={p for p,age in self.roles(new,ring)}
        return new,ring,g
    def accept(self,r):
        if r['kind']=='header':return
        version=r['label_version']
        if r['kind']=='immutable_label':
            parent=r['predecessor_label'];assert version not in self.labels
            if parent is None:assert r['action'] is None;state=self.seed
            else:assert parent<version and parent in self.labels;state=self.step(self.labels[parent],r['action'])
            self.labels[version]=state
        else:assert r['kind'] in ('open','unfinished_expansion') and version in self.labels;state=self.labels[version]
        mask,ring,g=state
        assert mask==r['done_mask'] and g==r['g'] and self.n-self.start-mask.bit_count()==r['h'] and self.roles(mask,ring)==r['roles']
def main():
    r=read(D/'report.json');assert sha(D/'report.json')=='cc36f031e37d7ea9d0973cbc95566793e2514b3d8997832938ecd5eb7b648931'
    evidence=read(D/'evidence-provenance.json');assert evidence['source_manifest_sha256']==sha(P/'experiments/r188-general-region-G-volume-prepared/source-provenance.json')
    for name,digest in evidence['files_sha256'].items():assert sha(name)==digest,name
    inv={x['sha256']:x for x in read(PREP/'inventory.json')}; counts=Counter();status=Counter();checked=proposals=improved=before=after=0;regions=nonzero=processed=attempted=reopens=stale=0;costs=[]
    for case,row in zip(lines(PREP/'inputs.jsonl.gz'),r['records'],strict=True):
        data=case['input'];key=fingerprint(data);initial_entry=inv[key];assert key==row['sha256'] and row['family']==case['family'];status[row['source_status']]+=1
        assert row['source_status']==initial_entry['source_status'] and row['before_copies']==initial_entry['before_copies']
        if row['before_copies'] is None:assert row['after_copies'] is None and row['actual_complete_outputs']==0;continue
        initial=next(lines(PREP/'initials'/f'{key}.json.gz'));base=replay(data,dict(initial,input_sha256=key));checked+=1;assert base==row['before_copies'];before+=base
        if base==0:assert row['candidate_outcome']=='verified_zero_copy_retained' and row['after_copies']==0;costs.append((len(data['instructions']),0));continue
        assert row['baseline_check']['outcome']=='verified';path=Path(row['complete_absolute_path']);assert path.drive.upper()=='G:' and sha(path)==row['complete_gzip_sha256']
        candidate_costs=[];decoded=0
        with gzip.open(path,'rb') as stream:
            for line in stream:
                decoded+=len(line);output=json.loads(line);saved=output['candidate'];start=output['region_start'];stop=min(len(data['instructions']),start+32)
                assert output['input_sha256']==key and saved['original_order'][:start]==initial['original_order'][:start] and saved['original_order'][stop:]==initial['original_order'][stop:]
                assert set(saved['original_order'][start:stop])==set(initial['original_order'][start:stop])
                candidate_costs.append(replay(data,dict(saved,input_sha256=key)));checked+=1;proposals+=1
        assert len(candidate_costs)==row['actual_complete_outputs'] and decoded==row['decoded_complete_bytes'] and path.stat().st_size==row['compressed_complete_bytes']
        best=next(lines(path.parent/f'{key[:16]}-best.json.gz'));final=replay(data,best);checked+=1
        assert final==row['after_copies']==min([base]+candidate_costs);after+=final;improved+=final<base;costs.append((len(data['instructions']),final))
        stats=row['stats'];assert stats['processed_states']<=20000 and stats['attempted_transitions']<=20000;processed+=stats['processed_states'];attempted+=stats['attempted_transitions']
        assert len(row['diagnostic_exports'])==len(stats['attempts'])
        for export,attempt in zip(row['diagnostic_exports'],stats['attempts']):
            path=Path(export['path']);assert path.drive.upper()=='G:' and sha(path)==export['compressed_sha256'] and path.stat().st_size==export['compressed_bytes']
            ring=Ring(data,initial,export['start']);local=Counter();digest=hashlib.sha256();decoded=0
            with gzip.open(path,'rb') as stream:
                for line in stream:
                    decoded+=len(line);digest.update(line);record=json.loads(line);local[record['kind']]+=1;ring.accept(record)
            assert dict(local)==export['counts'] and decoded==export['decoded_bytes'] and digest.hexdigest()==export['decoded_sha256']
            assert sum(local.values())-local['header']==export['independent_replayed_records'];counts.update(local);regions+=1;nonzero+=export['start']>0
            reopens+=attempt['stats']['reopens'];stale+=attempt['stats']['stale']
        print(json.dumps(dict(input=key[:16],whole_outputs=checked,labels=counts['immutable_label'])),flush=True)
    assert (checked,proposals,before,after,improved)==(5116,4680,192902,192859,23)
    assert dict(status)=={'proven_infeasible_under_model':47,'verified':272,'scheduling_failure':8,'budget_exhausted':9}
    assert dict(counts)==dict(header=1031,immutable_label=711769,open=60494,unfinished_expansion=323)
    assert len(costs)==272;mean=sum(c/(n+c) for n,c in costs)/272
    assert abs(mean-r['after_legal_copy_output_mean'])<1e-15 and r['all_input_quality_mean'] is None
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(D/'report.json'),original_inputs=336,legal_initials=272,retained_statuses=dict(status),before_COPY=before,after_COPY=after,improved_inputs=improved,complete_proposals=proposals,whole_outputs_independently_checked=checked,frontier_counts=dict(counts),regions=regions,nonzero_prefix_regions=nonzero,processed_states=processed,attempted_transitions=attempted,reopens=reopens,stale=stale,after_legal_copy_output_mean=mean,all_input_quality_mean=None,
        scope='All336 statuses retained and all5116whole outputs exact original identity/ordered operands/COPY age/RAW-WAR-WAW independently replayed. All711769immutable/60494OPEN/323unfinished records checked by independent root physical ring and masks, including nonzero original prefixes. Whole arithmetic follows original operation identities and register hazards, not candidate-generated numeric gold. Selfgenerated legal272 mean13.5842%,64 missingoutputs retained; partial restricted search does not prove global optimum/infeasibility or officialLevel1-3.',
        authorization='Analyze all retained family/COPY origins and search partials; identify one stronger scheduling/retention mechanism with full original counterexamples and primary literature before implementation. No default promotion or full score claim.')
    (ROOT/'outputs/stage2-root-general-region-full336-actual-r187.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
