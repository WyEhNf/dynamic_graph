"""Preserve the original failed R160 producer and partial raw control outputs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'experiments/r160-tree-pair-serial-controls'
target=folder/'failure-provenance.json'
if target.exists(): raise FileExistsError(target)
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
target.write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),'exit_code':1,
    'failure':'Restricted relay cannot progress in one fixed serial order; producer failed to classify expected restricted-order failure.',
    'evidence_sha256':hashes,'repair':'New R161 producer classifies only this exact schedule error; independent verify still fail closed. R160 not overwritten.'},indent=2)+'\n')
print(json.dumps({'files':len(hashes),'manifest':str(target.relative_to(ROOT))}))
