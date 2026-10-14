"""Audit new core certificates against archived independent oracle results."""
import argparse,hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.persistent_core_bound import persistent_core_bound,check_persistent_core_certificate
from isa_scheduler.model import parse_block
from isa_scheduler.evaluation import fingerprint
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--round',required=True);a=p.parse_args();folder=ROOT/'experiments'/a.round;folder.mkdir(exist_ok=False);source=ROOT/a.source
 original=json.loads((source/'report.json').read_text(encoding='utf-8'));reference={r['sha256']:r for r in original['records']};records=[];violations=[]
 if hashlib.sha256((source/'inputs.jsonl').read_bytes()).hexdigest()!=original['corpus_sha256']:raise ValueError('Oracle corpus hash mismatch')
 for case in map(json.loads,(source/'inputs.jsonl').read_text(encoding='utf-8').splitlines()):
  data=case['input'];sha=fingerprint(data);previous=reference[sha];certificate=persistent_core_bound(parse_block(data),time_budget_ms=1000)
  if certificate:
   lower=check_persistent_core_certificate(data,certificate)['verified_global_copy_lower_bound']
   item={'sha256':sha,'oracle_status':previous['status'],'oracle_copies':previous.get('copies'),'lower':lower,'certificate':certificate};records.append(item)
   if previous['status']=='optimal'and lower>previous['copies']:violations.append(item)
 report={'source':a.source,'oracle_report_sha256':hashlib.sha256((source/'report.json').read_bytes()).hexdigest(),'checked_cases':len(reference),'positive_certificates':len(records),
         'positive_statuses':dict(Counter(r['oracle_status']for r in records)),'violations':violations,'records':records}
 (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k!='records'}));return int(bool(violations))
if __name__=='__main__':raise SystemExit(main())
