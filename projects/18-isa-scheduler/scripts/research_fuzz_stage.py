"""Fresh 10000 small graphs, frozen-v14 pairing and four independent checks."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from isa_scheduler.fuzz import generate,minimize_dead_nodes
from research_benchmark import run_case

def main():
 p=argparse.ArgumentParser();p.add_argument('--round',required=True);p.add_argument('--count',type=int,default=10000);p.add_argument('--seed',type=int,default=18);p.add_argument('--strategy',default='research_portfolio');p.add_argument('--baseline',default='v14_auto');a=p.parse_args()
 if a.count<1 or not a.round.replace('-','').replace('_','').isalnum():raise ValueError('Positive count and safe round required')
 source=ROOT/'experiments'/(a.round+'-input');source.mkdir(exist_ok=False)
 cases=[];families=('wide','branch','highfanout','hazard')
 for index in range(a.count):
  family=families[index%4];bits=2+(index//4)%4;seed=a.seed+index;data=generate(seed,family,bits)
  cases.append({'family':family,'target_nodes':len(data['instructions']),'seed':seed,'input':data})
 corpus=source/'inputs.jsonl';corpus.write_text(''.join(json.dumps(case,separators=(',',':'))+'\n'for case in cases),encoding='utf-8')
 (source/'manifest.json').write_text(json.dumps({'count':a.count,'seed':a.seed,'source_sha256':hashlib.sha256(corpus.read_bytes()).hexdigest(),'source':'fixed deterministic synthetic small graphs; not official'},indent=2)+'\n',encoding='utf-8')
 command=[sys.executable,str(ROOT/'scripts/research_benchmark.py'),'--round',a.round,'--input',str(corpus),'--variants',a.baseline+','+a.strategy,'--before',a.baseline,'--after',a.strategy,'--time-budget-ms','100']
 status=subprocess.run(command,cwd=ROOT).returncode
 report_path=ROOT/'experiments'/a.round/'report.json'
 if not report_path.exists():return status or 2
 report=json.loads(report_path.read_text(encoding='utf-8'));lookup={record['sha256']:record for record in report['records']if record['variant']==a.strategy}
 counterexamples={}
 from isa_scheduler.evaluation import fingerprint
 for case in cases:
  data=case['input'];record=lookup[fingerprint(data)];kind=record['status']
  if kind=='verified' or kind in counterexamples:continue
  def still_failure(candidate):return run_case(candidate,a.strategy,100,30000)['status']==kind
  minimal=minimize_dead_nodes(data,still_failure)
  target=ROOT/'experiments'/a.round/(kind+'-minimal.json');target.write_text(json.dumps(minimal,indent=2)+'\n',encoding='utf-8')
  counterexamples[kind]={'path':target.name,'sha256':fingerprint(minimal),'scope':'minimum dependency-closed induced subgraph reproducing bounded same-status failure, <=10 original nodes; not global program minimality'}
 (ROOT/'experiments'/a.round/'counterexamples.json').write_text(json.dumps(counterexamples,indent=2)+'\n',encoding='utf-8')
 return status
if __name__=='__main__':raise SystemExit(main())
