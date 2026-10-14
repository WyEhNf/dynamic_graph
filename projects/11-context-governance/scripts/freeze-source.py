"""Preserve a non-overwriting module snapshot before a new measured batch."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True)
parser.add_argument('--intent',required=True)
args=parser.parse_args()
project=Path(__file__).resolve().parents[1]
destination=Path(args.output)
destination.mkdir(parents=True,exist_ok=False)
hashes={}
for source in sorted((project/'src'/'context_governance').glob('*.py')):
    shutil.copy2(source,destination/source.name)
    hashes[source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
(destination/'provenance.json').write_text(json.dumps({
    'frozen_unix':time.time(),'intent':args.intent,'source_sha256_at_freeze':hashes,
    'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'scope':'Python modules only; evaluation also records fixtures, model files and invocation.'
},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'modules':len(hashes),'output':str(destination.resolve())}))
