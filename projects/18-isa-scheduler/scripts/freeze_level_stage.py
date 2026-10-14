"""Freeze completed R91 provenance without rewriting its measured reports."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def manifest(folder):return {'isa_scheduler/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in folder.glob('*.py')}
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 current=manifest(ROOT/'isa_scheduler');snapshot=manifest(ROOT/'experiments/baseline_level_r91');frozen=manifest(ROOT/'experiments/baseline_v14/isa_scheduler')
 assert current==snapshot
 folder=ROOT/'experiments/milestone-level-r91-tests';destination=folder/'source-provenance.json'
 if destination.exists():raise ValueError('Already frozen; preserve evidence')
 paths=('experiments/milestone-level-r91-10000/report.json','experiments/milestone-level-r91-336/report.json')
 for path in paths:
  report=json.loads((ROOT/path).read_text(encoding='utf-8'))
  assert {k.replace('\\','/'):v for k,v in report['current_source_manifest_at_start'].items()}==current
 provenance={'frozen_utc':datetime.now(timezone.utc).isoformat(),'core_manifest':current,'core_aggregate_sha256':digest(current),
  'snapshot':'experiments/baseline_level_r91','v14_module':'experiments.baseline_v14.isa_scheduler.optimizer',
  'v14_manifest':frozen,'v14_aggregate_sha256':digest(frozen),
  'benchmark_harness_executed_copy':'research_benchmark-executed.py',
  'benchmark_harness_executed_sha256':hashlib.sha256((folder/'research_benchmark-executed.py').read_bytes()).hexdigest(),
  'reports':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()for path in paths},
  'tests':{'count':141,'elapsed_seconds':52.266,'path':'tests.log','sha256':hashlib.sha256((folder/'tests.log').read_bytes()).hexdigest()},
  'scope':'This freezes R91 only; later candidate code and harness experiments do not rewrite these reports or prior v14 evidence.',
  'counterexample_scope':'Dependency-closed diagnostic subgraphs may remove GET/SET and need not meet the official GET-root/SET-leaf shape; not claimed official-valid minimal failing inputs.'}
 destination.write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8');print(json.dumps({'path':str(destination),'core_aggregate_sha256':digest(current),'v14_aggregate_sha256':digest(frozen)}))
if __name__=='__main__':main()
