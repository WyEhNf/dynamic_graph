"""Analyze separately evaluated reverse candidates; no ideal choice deployment claim."""
import argparse,json,statistics
from collections import defaultdict
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source');a=p.parse_args();folder=Path(a.source);r=json.loads((folder/'report.json').read_text(encoding='utf-8'));groups=defaultdict(dict)
for row in r['records']:groups[row['sha256']][row['variant']]=row
summaries={}
for variant in ('reverse_pressure','reverse_cluster','reverse_span'):
 rows=[]
 for key,g in groups.items():
  old,new=g['v14_auto'],g[variant]
  row={'sha256':key,'family':old['family'],'bits':old['bit_width'],'nodes':old['node_count'],'before_status':old['status'],'after_status':new['status']}
  if old['status']==new['status']=='verified':row.update(delta=new['inserted_copies']-old['inserted_copies'],before_copies=old['inserted_copies'],after_copies=new['inserted_copies'],speedup=old['optimizer_ms']/max(new['optimizer_ms'],1e-9))
  rows.append(row)
 joint=[x for x in rows if 'delta'in x];gain=[x for x in joint if x['delta']<0]
 summaries[variant]={'joint':len(joint),'better':len(gain),'same':sum(x['delta']==0 for x in joint),'worse':sum(x['delta']>0 for x in joint),'rescued':sum(x['before_status']!='verified'and x['after_status']=='verified'for x in rows),'lost_outputs':sum(x['before_status']=='verified'and x['after_status']!='verified'for x in rows),'before_copies_joint':sum(x['before_copies']for x in joint),'after_copies_joint':sum(x['after_copies']for x in joint),'median_speedup_joint':statistics.median(x['speedup']for x in joint),
                     'gains_by_family':{family:{'count':sum(x['family']==family for x in gain),'copies_reduced':sum(-x['delta']for x in gain if x['family']==family)}for family in sorted({x['family']for x in gain})},'rows':rows}
(folder/'reverse-potential.json').write_text(json.dumps(summaries,indent=2)+'\n')
print(json.dumps({k:{a:b for a,b in v.items()if a!='rows'}for k,v in summaries.items()}))
