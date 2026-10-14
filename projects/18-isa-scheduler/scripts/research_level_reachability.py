"""Audit COPY-only lower bounds on EVERY saved input; no filtering by success."""
import argparse,csv,hashlib,json,statistics,sys
from collections import Counter,defaultdict
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.model import parse_block,InvalidBlock
from isa_scheduler.spine_copy_bound import spine_copy_bound,check_spine_copy_certificate
from isa_scheduler.consumer_copy_bound import consumer_copy_bound,check_consumer_copy_certificate
from isa_scheduler.pair_copy_bound import pair_copy_bound,check_pair_copy_certificate
from isa_scheduler.persistent_cut_bound import persistent_cut_bound,check_persistent_cut_certificate
from isa_scheduler.persistent_core_bound import persistent_core_bound,check_persistent_core_certificate
from isa_scheduler.reduction_copy_bound import reduction_copy_bound,check_reduction_copy_certificate
from isa_scheduler.model import BudgetExceeded

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',default='experiments/milestone-v14');p.add_argument('--round',default='level-reachability-v14');p.add_argument('--include-dag',action='store_true');p.add_argument('--include-core',action='store_true');p.add_argument('--include-reduction',action='store_true');a=p.parse_args()
 folder=ROOT/'experiments'/a.round;folder.mkdir(exist_ok=False);source=ROOT/a.source;started=perf_counter()
 previous=json.loads((source/'report.json').read_text(encoding='utf-8'));status={r['sha256']:r['status']for r in previous['records']if r['variant']==previous['paired_variants']['after']}
 records=[]
 for case in map(json.loads,(source/'inputs.jsonl').read_text(encoding='utf-8').splitlines()):
  data=case['input'];block=parse_block(data);proofs=[]
  candidates=[(spine_copy_bound,check_spine_copy_certificate),(consumer_copy_bound,check_consumer_copy_certificate),(pair_copy_bound,check_pair_copy_certificate)]
  if a.include_dag:candidates.append((persistent_cut_bound,check_persistent_cut_certificate))
  if a.include_core:candidates.append((persistent_core_bound,check_persistent_core_certificate))
  if a.include_reduction:candidates.append((reduction_copy_bound,check_reduction_copy_certificate))
  for propose,check in candidates:
   try:
    certificate=propose(block)
    if certificate:
     independent=check(data,certificate);assert independent['verified_global_copy_lower_bound']>=certificate['copy_lower_bound'];proofs.append({'certificate':certificate,'independent':independent})
   except (InvalidBlock,BudgetExceeded):continue
  lower=max((r['certificate']['copy_lower_bound']for r in proofs),default=0);n=len(data['instructions']);sha=fingerprint(data)
  records.append({'sha256':sha,'family':case['family'],'seed':case['seed'],'bit_width':data['bit_width'],'original_nodes':n,'previous_status':status[sha],
                  'copy_lower_bound':lower,'lower_copy_per_original':lower/n if n else 0,'lower_copy_per_output':lower/(n+lower)if n+lower else 0,
                  'exceeds_10pct_both_denominators':lower/(n+lower)>.1 if n+lower else False,'exceeds_2pct_both_denominators':lower/(n+lower)>.02 if n+lower else False,'proofs':proofs})
 def summary(rows):
  return {'count':len(rows),'statuses':dict(Counter(r['previous_status']for r in rows)),
          'mean_lower_copy_per_original':statistics.mean(r['lower_copy_per_original']for r in rows),
          'mean_lower_copy_per_output':statistics.mean(r['lower_copy_per_output']for r in rows),
          'individual_inputs_exceed_10pct':sum(r['exceeds_10pct_both_denominators']for r in rows),'individual_inputs_exceed_2pct':sum(r['exceeds_2pct_both_denominators']for r in rows)}
 groups=defaultdict(list)
 for r in records:groups[r['family']].append(r)
 result={'source':a.source,'scope':'Distinct original nodes once, COPY-only, original ordered operands and memory hazards. No aliases/recompute/rereads/spill. Lower bounds are NOT official pass/fail and denominator still unspecified.',
         'all_inputs':summary(records),'previous_successes_only':summary([r for r in records if r['previous_status']=='verified']),
         'families':{k:summary(v)for k,v in groups.items()},'elapsed_seconds':perf_counter()-started,
         'corpus_sha256':hashlib.sha256((source/'inputs.jsonl').read_bytes()).hexdigest(),'source_manifest':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in (ROOT/'isa_scheduler').glob('*.py')},'records':records}
 (folder/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 with (folder/'records.csv').open('w',encoding='utf-8-sig',newline='')as f:
  keys=[k for k in records[0]if k!='proofs'];w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:r[k]for k in keys}for r in records)
 print(json.dumps({k:v for k,v in result.items()if k not in ('records','source_manifest','families')},ensure_ascii=False))
 print(json.dumps({'family_floors':{k:v for k,v in result['families'].items()if v['mean_lower_copy_per_output']>.02}},ensure_ascii=False))
if __name__=='__main__':main()
