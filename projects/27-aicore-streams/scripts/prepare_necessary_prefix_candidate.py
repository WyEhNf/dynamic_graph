"""Isolated R57 candidate; R51 default and R56 negative evidence remain intact."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/batch57'


def main():
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    original=ROOT/'solution/solution.cpp'
    assert sha(original)=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
    text=original.read_text(encoding='utf-8')
    namespace_end=text.index('\n} // namespace aicore_detail') if '\n} // namespace aicore_detail' in text else -1
    if namespace_end<0:
        marker='\nI AicoreLastMetric'
        boundary=text.index(marker)
        namespace_end=text.rfind('\n}',0,boundary)
    text=text[:namespace_end]+'\n#include "necessary_prefix_search.inc"\n'+text[namespace_end:]
    needle='  metrics.micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();\n  if(!found) throw'
    insert='''  if(!found && graph.n<=512) {
    auto searched=necessary_prefix_search(hw,graph);
    if(static_cast<int>(searched.order.size())==graph.n) {
      budget=metrics.candidates+5;
      consider(searched.order,std::vector<int>(graph.n,0),1,0,{},true);
      for(int s:std::set<int>{std::min(largest,4),std::min(largest,8)})if(s>1) {
        auto assignment=assign(hw,graph,searched.order,s,0);
        consider(searched.order,assignment,s);consider(searched.order,assignment,s,2);
      }
    }
  }
'''
    if text.count(needle)!=1:raise AssertionError('fallback location')
    text=text.replace(needle,insert+needle)
    with (OUT/'solution.cpp').open('x',encoding='utf-8') as stream:stream.write(text)
    driver=(ROOT/'research/batch56/selected12-driver.cpp').read_text()
    driver=driver.replace('argc!=3','argc!=3 && argc!=4').replace('projection_memory_search(h,g)','necessary_prefix_search(h,g)')
    driver=driver.replace('<<result.evaluations','<<result.states').replace('<<result.best_peak.lo','<<result.prunes').replace('<<result.best_peak.hi','<<result.monitored_targets')
    driver=driver.replace('try{whole=ScheduleCvGraph','try{if(argc==4)throw std::runtime_error("helper-only");whole=ScheduleCvGraph')
    with (OUT/'selected-driver.cpp').open('x',encoding='utf-8') as stream:stream.write(driver)
    manifest={'default_changed':False,'work_limit':2000000,'max_nodes':512,'max_targets':64,'branch_limit':8,
        'scope':'completed serial prefixes, input-only necessary bounds, unknown on any failure',
        'sha256':{str(p.relative_to(ROOT)):sha(p) for p in [original,OUT/'solution.cpp',OUT/'necessary_prefix_search.inc',OUT/'selected-driver.cpp',Path(__file__)]}}
    (OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest))


if __name__=='__main__':main()
