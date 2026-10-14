"""R58 experiment: canonical safe prefixes and exact done-set transpositions."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/batch58'
OUT.mkdir(exist_ok=True)
source=(ROOT/'research/batch57/necessary_prefix_search.inc').read_text()
source=source.replace('I work=0,prunes=0,states=0;', 'I work=0,prunes=0,states=0,memo_hits=0,safe_steps=0;')
source=source.replace('I limit=2000000', 'I limit=8000000').replace('g.n>512','g.n>768')
source=source.replace('  I live=0;', '''  std::vector<unsigned long long> mask((g.n+63)/64);
  std::set<std::vector<unsigned long long>> failed_policy;
  I live=0;''')
source=source.replace('    struct Choice{', '''    if(failed_policy.count(mask)){++result.memo_hits;return false;}
    struct Choice{''')
source=source.replace('    if(ready.size()>static_cast<size_t>(branch_limit))ready.resize(branch_limit);', '''    // A feasible ready nonpositive-net task can be exchanged leftward:
    // its released parents have no other unfinished user, and live never rises.
    // All future-BEGIN necessary constraints are still checked above.
    if(!ready.empty() && g.v[ready[0].node].output_memory<=ready[0].released){ready.resize(1);++result.safe_steps;}
    else if(ready.size()>static_cast<size_t>(branch_limit))ready.resize(branch_limit);''')
source=source.replace('done[p]=1;order.push_back(p);', 'done[p]=1;mask[p/64]|=1ull<<(p%64);order.push_back(p);')
source=source.replace('order.pop_back();done[p]=0;live=old_live;', 'order.pop_back();done[p]=0;mask[p/64]&=~(1ull<<(p%64));live=old_live;')
source=source.replace('    return false;\n  };', '''    // A policy dead-end, not an infeasibility certificate: branch_limit is heuristic.
    // Equal done sets determine live, degrees, users, target slack and choices.
    if(failed_policy.size()<100000)failed_policy.insert(mask);
    return false;
  };''')
(OUT/'necessary_prefix_search.inc').write_text(source)
solution=(ROOT/'research/batch57/solution.cpp').read_text().replace('if(!found && graph.n<=512) {\n    auto searched=necessary_prefix_search', 'if(!found && graph.n<=768) {\n    auto searched=necessary_prefix_search')
(OUT/'solution.cpp').write_text(solution)
driver=(ROOT/'research/batch57/selected-driver.cpp').read_text()
driver=driver.replace('<<result.monitored_targets', '<<result.monitored_targets<<",\\\"memo_hits\\\":"<<result.memo_hits<<",\\\"safe_steps\\\":"<<result.safe_steps')
(OUT/'selected-driver.cpp').write_text(driver)
manifest={'candidate':'R58','default_changed':False,'work_limit':8000000,'max_nodes':768,'branch_limit':8,
          'memo_semantics':'fully completed branch-limited policy failure only; never interrupted states',
          'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*') if p.suffix in ('.cpp','.inc')}}
(OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest))
