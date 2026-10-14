"""R63 fixed recovery policy selected from declared R62 ablations."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/batch63';OUT.mkdir(exist_ok=True)
source=(ROOT/'research/batch62/macro_prefix_search.inc').read_text().replace('MacroPrefixResult macro_prefix_search(', 'MacroPrefixResult macro_prefix_beam(')
source+='''
// Recovery only, after every pre-existing candidate failed. All decisions use
// the input graph; no corpus identifiers, known orders, or witness data enter.
MacroPrefixResult macro_prefix_search(const HardwareInfo& h,const Graph& g,I limit=160000000) {
  MacroPrefixResult total;
  for(int style=0;style<3;++style) {
    if(style && g.n>512)break;
    I allowance=std::min<I>(style?16000000:128000000,limit-total.work);
    if(allowance<=0){total.exhausted=true;break;}
    auto r=macro_prefix_beam(h,g,allowance,32,style);
    total.work+=r.work;total.prunes+=r.prunes;total.states+=r.states;total.memo_hits+=r.memo_hits;
    total.safe_steps+=1;total.monitored_targets=std::max(total.monitored_targets,r.monitored_targets);
    total.exhausted=total.exhausted || r.exhausted;
    if(r.order.size()==static_cast<size_t>(g.n)){total.order=std::move(r.order);return total;}
  }
  return total;
}
'''
(OUT/'macro_prefix_search.inc').write_text(source)
(OUT/'solution.cpp').write_text((ROOT/'research/batch62/solution.cpp').read_text())
driver=(ROOT/'research/batch62/selected-driver.cpp').read_text()
begin=driver.index('macro_prefix_search(h,g,');end=driver.index(';',begin)
driver=driver[:begin]+'macro_prefix_search(h,g,argc>=5?std::stoll(argv[4]):160000000)'+driver[end:]
(OUT/'selected-driver.cpp').write_text(driver)
# Standalone submission candidate carries no local .inc dependency.
(OUT/'single-file-solution.cpp').write_text((OUT/'solution.cpp').read_text().replace('#include "macro_prefix_search.inc"',source))
manifest={'candidate':'R63','default_changed':False,'max_total_work':160000000,'beam_width':32,
          'stages':[{'style':0,'work':128000000,'max_nodes':4096},{'style':1,'work':16000000,'max_nodes':512},{'style':2,'work':16000000,'max_nodes':512}],
          'policy':'only after R51 fails; each returned complete original order replayed and parallel schedule independently simulated',
          'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*') if p.suffix in ('.cpp','.inc')}}
(OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
