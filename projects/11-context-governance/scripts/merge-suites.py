"""Copy unchanged fixed suites with explicit split provenance; never overwrite."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

from context_governance.bundles import load_case

parser=argparse.ArgumentParser()
parser.add_argument('--sources',nargs='+',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--version',type=int,required=True)
args=parser.parse_args()
destination=Path(args.output)
if destination.exists(): raise ValueError('Destination must be new')
ids=[]; origins=[]; planned=[]
for origin in map(Path,args.sources):
    manifest_path=origin/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    for case_id in manifest['case_ids']:
        if case_id in ids: raise ValueError('Duplicate case ID')
        load_case(origin,case_id)
        ids.append(case_id); planned.append((origin,case_id))
    origins.append({'path':str(origin),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                    'case_ids':manifest['case_ids']})
destination.mkdir(parents=True)
for origin,case_id in planned:
    for folder,suffix in [('metadata','.json'),('spec','.md'),('oracle','.py'),('tests','.py')]:
        (destination/folder).mkdir(exist_ok=True)
        shutil.copy2(origin/folder/(case_id+suffix),destination/folder/(case_id+suffix))
    metadata=json.loads((origin/'metadata'/(case_id+'.json')).read_text(encoding='utf-8'))
    bundle=metadata['baseline_bundle']
    shutil.copytree(origin/'repo_bundles'/bundle,destination/'repo_bundles'/bundle)
    load_case(destination,case_id)
first=Path(args.sources[0])/'templates'
if first.exists(): shutil.copytree(first,destination/'templates')
manifest={'version':args.version,'case_ids':ids,'origins':origins,'constructed_unix':time.time(),
          'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'scope':'Unchanged source suites. Read origins for separate development and new holdout groups; not a fresh combined holdout.'}
(destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(ids),'output':str(destination.resolve())}))
