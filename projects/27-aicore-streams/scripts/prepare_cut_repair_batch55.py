"""Materialize isolated R55 from the exact R51 source; no compiler/candidate."""
from pathlib import Path
import hashlib,json
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=Path('solution/solution.cpp');assert sha(source)=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
text=source.read_text(encoding='utf-8');anchor='ReleaseCut release_cut_probe(const HardwareInfo& h,const Graph& g,int producer,'
assert text.count(anchor)==1
helper=Path('research/batch55/repair.cpp.inc').read_text(encoding='utf-8');text=text.replace(anchor,helper+'\n'+anchor)
start=text.index(anchor);end=text.index('ShallowResult release_cut_order(',start)
old='    if(selected<0)return r;'
assert text[start:end].count(old)==1
replacement='''    if(selected<0) {
      auto repair=failed_cut_beam_repair(h,g,producer,r.pending,remaining_users,remaining_degree,r.final_live,work,limit);
      if(!charge(2))return r; // Pay new result-status predicates before inspecting them.
      if(repair.valid)return repair;
      if(repair.exhausted)r.exhausted=true;
      return r;
    }'''
text=text[:start]+text[start:end].replace(old,replacement)+text[end:]
out=Path('research/batch55/solution.cpp');out.write_text(text,encoding='utf-8',newline='\n')
doc=dict(status='SOURCE_ONLY_MATERIALIZED_NOT_COMPILED',source_sha256=sha(out),base_sha256=sha(source),fragment_sha256=sha('research/batch55/repair.cpp.inc'),changes=['add compact original-user cut repair helper','only original ready-no-fit return dispatches repair; success and other rejection branches identical'],unchanged_default=True)
Path('research/batch55/source-provenance.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps(doc))
