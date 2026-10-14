"""R61: replay candidate closures in place and copy only retained beam states."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/batch61';OUT.mkdir(exist_ok=True)
source=(ROOT/'research/batch60/macro_prefix_search.inc').read_text()
start=source.index('  std::vector<State> beam;');end=source.index('  for(auto& state:beam)',start)
source=source[:start]+'''  auto less=[](const State& a,const State& b){return std::tie(a.live,a.peak,a.area,a.mask)<std::tie(b.live,b.peak,b.area,b.mask);};
  auto rollback=[&](State& s,size_t length,I live,I peak,I area) {
    while(s.order.size()>length) {
      int i=s.order.back();s.order.pop_back();s.done[i]=0;s.mask[i/64]&=~(1ull<<(i%64));
      for(int p:g.in[i])++s.users[p];
    }
    s.live=live;s.peak=peak;s.area=area;
  };
  std::vector<State> beam;beam.push_back(std::move(initial));
  for(int depth=0;depth<k;++depth) {
    std::vector<State> next;std::set<std::vector<unsigned long long>> seen;
    for(auto& state:beam)for(int q=0;q<k;++q) {
      if(!charge(1+static_cast<I>(projection.predecessors[q].size())))return result;
      if(state.done[targets[q]])continue;
      bool ready=true;for(int p:projection.predecessors[q])if(!state.done[targets[p]])ready=false;if(!ready)continue;
      const size_t length=state.order.size();const I live=state.live,peak=state.peak,area=state.area;++result.states;
      for(int i:projection.closures[q])if(!append(state,i)){ready=false;break;}
      if(result.exhausted)return result;
      // Reserve rollback cost; even rejected partial closures restore all users.
      if(!charge(static_cast<I>(state.order.size()-length))){rollback(state,length,live,peak,area);return result;}
      if(ready) {
        if(!charge(static_cast<I>(state.mask.size()))){rollback(state,length,live,peak,area);return result;}
        if(!seen.insert(state.mask).second)++result.memo_hits;
        else if(next.size()<static_cast<size_t>(width) || less(state,next.front())) {
          if(!charge(2*static_cast<I>(g.n)+static_cast<I>(state.order.size()+state.mask.size()))){rollback(state,length,live,peak,area);return result;}
          if(next.size()==static_cast<size_t>(width)){std::pop_heap(next.begin(),next.end(),less);next.pop_back();}
          next.push_back(state);std::push_heap(next.begin(),next.end(),less);
        }
      }
      rollback(state,length,live,peak,area);
    }
    if(next.empty())return result;
    std::sort(next.begin(),next.end(),less);beam=std::move(next);
  }
''' + source[end:]
(OUT/'macro_prefix_search.inc').write_text(source)
(OUT/'solution.cpp').write_text((ROOT/'research/batch60/solution.cpp').read_text())
(OUT/'selected-driver.cpp').write_text((ROOT/'research/batch60/selected-driver.cpp').read_text())
manifest={'candidate':'R61','default_changed':False,'work_limit':128000000,'max_nodes':4096,'beam_width':64,
          'change':'exact same candidate ordering as R60, in-place closure replay/rollback, bounded max-heap of retained states',
          'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*') if p.suffix in ('.cpp','.inc')}}
(OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
