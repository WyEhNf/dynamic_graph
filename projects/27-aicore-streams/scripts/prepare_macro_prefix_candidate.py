"""Freeze a new input-only macro prefix beam candidate without altering R51."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/batch59';OUT.mkdir(exist_ok=True)
source=(ROOT/'research/batch57/solution.cpp').read_text().replace('necessary_prefix_search.inc','macro_prefix_search.inc').replace('necessary_prefix_search(hw,graph)','macro_prefix_search(hw,graph)').replace('if(!found && graph.n<=512) {\n    auto searched=macro_prefix_search','if(!found && graph.n<=4096) {\n    auto searched=macro_prefix_search')
(OUT/'solution.cpp').write_text(source)
driver=(ROOT/'research/batch58/selected-driver.cpp').read_text().replace('necessary_prefix_search(h,g)','macro_prefix_search(h,g)')
(OUT/'selected-driver.cpp').write_text(driver)
manifest={'candidate':'R59','default_changed':False,'work_limit':32000000,'max_nodes':4096,'beam_width':32,
          'policy':'workspace target closure beam; equal complete sets deduplicate; original direct lifetimes replayed',
          'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*') if p.suffix in ('.cpp','.inc')}}
(OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
