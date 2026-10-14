"""Isolated R51 -> R53 single change; freeze charges BEFORE generating gold."""
from pathlib import Path
import hashlib,json

P=Path('research/batch53');P.mkdir(exist_ok=True)
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
source=Path('solution/solution.cpp').read_text(encoding='utf-8')
assert sha('solution/solution.cpp')=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
fragment=r'''// Exact final-live dominance at ONE completed prefix. Logical work units
// cover every new traversal, state test, count, memory read and arithmetic.
// This is not a cycle count. Existing 4n copying and all old charges remain.
bool release_cut_final_dominated(const Graph& g,
 const std::vector<int>& pending,const std::vector<unsigned char>& included,
 const std::vector<unsigned char>& completed,const std::vector<int>& remaining_users,
 I live,I incumbent,I& work,I limit,ProfileInteger& final,bool& dominated) {
  auto charge=[&](I amount){return cut_charge(work,limit,amount);};
  if(!charge(g.n))return false; // zero-initialize n counters
  std::vector<int> hits(g.n),touched;
  for(int i:pending) {
    if(!charge(1))return false; // pending-node traversal
    for(int p:g.in[i]) {
      if(!charge(2))return false; // original edge + completed-parent test
      if(completed[p]) {
        if(!charge(2))return false; // first-hit test + increment
        if(!hits[p]++)touched.push_back(p);
      }
    }
  }
  I retained=live;
  for(int p:touched) {
    if(!charge(2))return false; // distinct-parent traversal + users comparison
    if(hits[p]==remaining_users[p]) {
      if(!charge(3))return false; // output read + nonnegative guard + subtract
      if(g.v[p].output_memory>retained)throw std::logic_error("Invalid physical cut prefix");
      retained-=g.v[p].output_memory;
    }
  }
  if(!charge(1))return false; // exact wide conversion
  final=ProfileInteger(retained);
  for(int i:pending) {
    if(!charge(2))return false; // node traversal + original sink test
    bool held=g.out[i].empty();
    if(!held)for(int c:g.out[i]) {
      if(!charge(3))return false; // original edge + done + included tests
      if(!completed[c] && !included[c]){held=true;break;}
    }
    if(held) {
      if(!charge(2))return false; // output read + exact wide addition
      final+=ProfileInteger(g.v[i].output_memory);
    }
  }
  if(!charge(1))return false; // strict wide comparison; equality not pruned
  dominated=ProfileInteger(incumbent)<final;return true;
}

'''
anchor='ReleaseCut release_cut_probe('
assert source.count(anchor)==1
source=source.replace(anchor,fragment+anchor)
old='I live,I& work,I limit) {\n  ReleaseCut r;r.peak=r.final_live=live;'
new='I live,I& work,I limit,const I* incumbent_final=nullptr) {\n  ReleaseCut r;r.peak=r.final_live=live;'
assert source.count(old)==1;source=source.replace(old,new)
old='  bool valid=false,exhausted=false;\n};\nbool cut_charge'
new='  bool valid=false,exhausted=false,pruned=false;\n};\nbool cut_charge'
assert source.count(old)==1;source=source.replace(old,new)
old='  for(int i:g.topo){if(!charge(1))return r;if(included[i])r.pending.push_back(i);}\n  while(r.order.size()<r.pending.size()) {'
new='''  for(int i:g.topo){if(!charge(1))return r;if(included[i])r.pending.push_back(i);}
  if(!charge(1))return r; // new incumbent-presence branch
  if(incumbent_final) {
    ProfileInteger exact;bool dominated=false;
    if(!release_cut_final_dominated(g,r.pending,included,completed,remaining_users,
       live,*incumbent_final,work,limit,exact,dominated)){r.exhausted=true;return r;}
    if(dominated){r.pruned=true;return r;} // invalid optional candidate, not a plan
  }
  while(r.order.size()<r.pending.size()) {'''
assert source.count(old)==1;source=source.replace(old,new)
old='      auto candidate=release_cut_probe(h,g,p,done,users,degree,live,r.work,limit);++r.evaluations;'
new='''      if(!charge(1))return r; // current-prefix incumbent parameter selection
      auto candidate=release_cut_probe(h,g,p,done,users,degree,live,r.work,limit,have?&selected.final_live:nullptr);++r.evaluations;'''
assert source.count(old)==1;source=source.replace(old,new)
(P/'solution.cpp').write_text(source,encoding='utf-8',newline='\n')
(P/'final-live.cpp.inc').write_text(fragment,encoding='utf-8',newline='\n')
table=dict(schema='cut-logical-operation-charges-r53-v1',status='FROZEN_BEFORE_GOLD',units='Deterministic logical work units, not CPU instructions/cycles; bundled short-circuit tests charged upfront. All previous charges unchanged.',budgets=dict(cut=2000000,total=16000000,closure=128,held_top=24,seeds_unchanged=True),operations=[
 dict(location='outer each producer before probe',amount=1,operation='current-prefix have conditional / incumbent parameter selection'),
 dict(location='probe after complete pending, <=128',amount=1,operation='incumbent presence branch; no-incumbent does no final calculation'),
 dict(location='final bound entry',amount='n',operation='zero initialization of hits[n]'),
 dict(location='first pending loop',amount=1,operation='node traversal'),
 dict(location='each scanned original input',amount=2,operation='edge traversal and completed-parent test'),
 dict(location='each completed-parent hit',amount=2,operation='first-hit test / distinct touched append bookkeeping and hits increment'),
 dict(location='each distinct touched parent',amount=2,operation='traversal and hits == remaining_users comparison'),
 dict(location='each released distinct parent',amount=3,operation='output read, retained>=output guard, retained subtraction'),
 dict(location='before final wide value',amount=1,operation='nonnegative int64 -> ProfileInteger conversion'),
 dict(location='second pending loop',amount=2,operation='node traversal and original-sink test'),
 dict(location='each original output edge visited until first external user',amount=3,operation='edge traversal, completed-user and included-user tests, bundled even if short-circuited'),
 dict(location='each final held cut node',amount=2,operation='output read and exact wide addition (including carry)'),
 dict(location='bound terminal',amount=1,operation='strict ProfileInteger comparison, equality never prunes')],failure='Before each bundled operation reserve its complete charge; if amount>remaining, setwork=limit and exhausted; no refund or partly valid candidate',range='retained release sums subset physical live<=MAX; final <=4096*MAX<2^75; hits<=4096 original distinct edges; no saturation, signed cast of wide result, or state mutation')
(P/'charged-work-table.json').write_text(json.dumps(table,indent=2)+'\n',encoding='utf-8')
files=['solution/solution.cpp','include/problem.h','research/batch51/provenance.json','reports/project27-research.tex','research/batch53/static-freeze.json','research/batch53/gold-declaration.json','research/batch53/solution.cpp','research/batch53/final-live.cpp.inc','research/batch53/charged-work-table.json','scripts/prepare_final_live_batch53.py']
manifest=dict(status='PRE_GOLD_SOURCE_AND_CHARGES_FROZEN',candidate_source_sha256=sha(P/'solution.cpp'),files=[dict(path=f,sha256=sha(f)) for f in files],gold_executed=False,default_changed=False)
(P/'pre-gold-freeze.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(candidate_source_sha256=manifest['candidate_source_sha256'],charged_table_sha256=sha(P/'charged-work-table.json'),pre_gold_freeze_sha256=sha(P/'pre-gold-freeze.json')),indent=2))
