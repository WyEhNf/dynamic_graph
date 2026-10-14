"""R60 input-only interface selection and bounded wider macro beam."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/batch60';OUT.mkdir(exist_ok=True)
base=(ROOT/'solution/solution.cpp').read_text();start=base.index('WorkspaceProjection workspace_projection(');end=base.index('\nstruct ProjectionProfile',start)
projection=base[start:end].replace('workspace_projection(', 'macro_workspace_projection(')
projection=projection.replace('I threshold=priority_mul_div(positive[(positive.size()-1)/2],4,1);','I threshold=std::max<I>(1,positive.back()/4);')
projection=projection.replace('s.targets.size()>512','s.targets.size()>1024')
source=(ROOT/'research/batch59/macro_prefix_search.inc').read_text().replace('I limit=32000000,int width=32','I limit=128000000,int width=64')
source=source.replace('workspace_projection(g)','macro_workspace_projection(g)')
(OUT/'macro_prefix_search.inc').write_text(projection+'\n'+source)
(OUT/'solution.cpp').write_text((ROOT/'research/batch59/solution.cpp').read_text())
driver=(ROOT/'research/batch59/selected-driver.cpp').read_text().replace('argc!=3 && argc!=4','argc<3 || argc>6').replace('if(argc==4)','if(argc>=4)')
driver=driver.replace('macro_prefix_search(h,g)', 'macro_prefix_search(h,g,argc>=5?std::stoll(argv[4]):128000000,argc>=6?std::stoi(argv[5]):64)')
(OUT/'selected-driver.cpp').write_text(driver)
manifest={'candidate':'R60','default_changed':False,'work_limit':128000000,'max_nodes':4096,'max_targets':1024,'beam_width':64,
          'selection':'local workspace maxima with at least two direct inputs, W >= max_W/4',
          'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*') if p.suffix in ('.cpp','.inc')}}
(OUT/'source-provenance.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
