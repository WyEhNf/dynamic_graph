"""Prepared direct serial controls. Run only after root releases CPU window."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.diagnose_tree_dfs_gap import materialize
from scripts.research_spine_age_probe import check


def main():
    source = ROOT / 'experiments/r158-tree-fixed-pair-diagnostic'
    folder = ROOT / 'experiments/r160-tree-pair-serial-controls'; folder.mkdir(exist_ok=False)
    paths = [Path(__file__), ROOT / 'scripts/diagnose_tree_dfs_gap.py', ROOT / 'scripts/tree_raw_oracles.py',
             ROOT / 'scripts/research_spine_age_probe.py', ROOT / 'research/level-stage/tree-subtree-interleave-proof.md']
    hashes = {}
    for p in paths:
        target = folder / 'src' / p.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target); hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (folder / 'source-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':hashes,'scope':'Independent both-concat controls only; no new DP/oracle/baseline rescheduling'},indent=2)+'\n')
    cases = {case['family']: case['input'] for case in map(json.loads,(source/'inputs.jsonl').read_text().splitlines())}
    old = json.loads((source/'report.json').read_text()); records=[]
    for row in old['records']:
        data=cases[row['family']]; key=row['input_sha256']; saved=json.loads((source/(key[:16]+'-baseline-output.json')).read_text())
        recreated=materialize(data,saved['original_order'])
        if recreated['optimized_instructions'] != saved['output']['optimized_instructions']:
            raise AssertionError('Raw deadline policy does not match actual baseline; controls fail closed')
        start,stop=row['stats']['rank_interval']; sides=row['stats']['sides']; serial=[]
        for orientation in ((0,1),(1,0)):
            middle=list(sides[orientation[0]])+list(sides[orientation[1]])+[row['parent']]
            order=saved['original_order'][:start]+middle+saved['original_order'][stop+1:]
            output=materialize(data,order); check(data,output,order)
            copies=sum(n['op']=='COPY' for n in output['optimized_instructions']); serial.append(copies)
            (folder/(key[:16]+f'-parent{row["parent"]}-serial{orientation[0]}-output.json')).write_text(json.dumps({'output':output,'original_order':order,'copies':copies})+'\n')
        records.append({'input_sha256':key,'family':row['family'],'parent':row['parent'],
            'incumbent_copies':row['before_copies'],'fixed_pair_copies':row['after_copies'],
            'serialAB_copies':serial[0],'serialBA_copies':serial[1],
            'gain_beyond_both_serial':min(serial)-row['after_copies']})
    result={'count':len(records),'records':records,
        'positive_beyond_both_serial':sum(r['gain_beyond_both_serial']>0 for r in records),
        'scope':'Full unchanged blocks, independent both-fixed-side serial controls with exact saved baseline policy reproduced. No global COPY optimality or composition.'}
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*') if p.is_file()}
    (folder/'evidence-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':hashes},indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__': main()
