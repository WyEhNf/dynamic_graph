"""Compare every archived lower bound with independently checked output cost.

This is an additional falsification check, not a replacement for a theorem or
complete oracle. No output is reconstructed from a different solver's witness.
"""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--bounds',required=True);p.add_argument('--outputs',required=True);p.add_argument('--destination',required=True);a=p.parse_args()
 bounds=ROOT/a.bounds;outputs=ROOT/a.outputs;destination=ROOT/a.destination
 if destination.exists():raise FileExistsError(destination)
 lb=json.loads(bounds.read_text(encoding='utf-8'));report=json.loads(outputs.read_text(encoding='utf-8'))
 variant=report['paired_variants']['after'];rows={r['sha256']:r for r in report['records']if r['variant']==variant and r['status']=='verified'}
 comparisons=[];contradictions=[]
 for r in lb['records']:
  if r['sha256']not in rows:continue
  row=rows[r['sha256']]
  if row.get('identity_check_status')!='verified':raise ValueError('Saved output has no independent original identity check')
  item={'sha256':r['sha256'],'family':r['family'],'lower':r['copy_lower_bound'],'copies':row['inserted_copies']}
  comparisons.append(item)
  if item['lower']>item['copies']:contradictions.append(item)
 result={'scope':'falsification against saved identity-checked outputs; not a proof of the lower-bound formula',
         'compared':len(comparisons),'contradictions':contradictions,'comparisons':comparisons,
         'bounds_sha256':hashlib.sha256(bounds.read_bytes()).hexdigest(),'outputs_report_sha256':hashlib.sha256(outputs.read_bytes()).hexdigest()}
 destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items()if k!='comparisons'}))
 if contradictions:sys.exit(1)
if __name__=='__main__':main()
