"""Static extraction from frozen R158 files; no emit/search/oracle invocation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'experiments/r158-tree-fixed-pair-diagnostic'
    folder = ROOT / 'experiments/r159-tree-pair-static-summary'; folder.mkdir(exist_ok=False)
    report = json.loads((source / 'report.json').read_text()); records = []
    for row in report['records']:
        a = set(row['stats']['sides'][0]); start, stop = row['stats']['rank_interval']
        outlets = []
        for path in source.glob(row['input_sha256'][:16] + '-parent' + str(row['parent']) + '-outlet*-output.json'):
            output = json.loads(path.read_text()); roles = [0 if n in a else 1 for n in output['original_order'][start:stop]]
            switches = sum(x != y for x, y in zip(roles, roles[1:]))
            outlets.append({'path': str(path.relative_to(ROOT)), 'copies': output['copies'], 'local_copies': output['local_copies'],
                            'side_switches': switches, 'original_order': output['original_order']})
        serial = [v['copies'] for v in outlets if v['side_switches'] <= 1]
        mixed = [v['copies'] for v in outlets if v['side_switches'] > 1]
        records.append({'parent': row['parent'], 'family': row['family'], 'before_copies': row['before_copies'],
                        'best_copies': row['after_copies'], 'retained_serial_min': min(serial) if serial else None,
                        'retained_mixed_min': min(mixed) if mixed else None, 'outlets': outlets})
        if row['family'] == 'ragged_tree' and row['parent'] == 59:
            best = min(outlets, key=lambda v: v['copies'])
            shutil.copy2(ROOT / best['path'], folder / 'ragged64-after-output.json')
            shutil.copy2(source / (row['input_sha256'][:16] + '-baseline-output.json'), folder / 'ragged64-before-output.json')
            case = next(case for case in map(json.loads, (source / 'inputs.jsonl').read_text().splitlines())
                        if case['family'] == 'ragged_tree')
            (folder / 'ragged64-input.json').write_text(json.dumps(case['input'], indent=2) + '\n')
    result = {'records': records, 'scope': 'Static frozen output reading only. Retained serial outlets are not an exhaustive serial orientation comparison: a serial state/path may have been merged with a cheaper mixed path. Need direct both-concat full-block replay before attributing all gain to interleaving.',
              'current_claim': 'One complete unchanged ragged64 block verified23->21; no composition/whole-corpus claim.'}
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*') if p.is_file()}
    (folder / 'evidence-provenance.json').write_text(json.dumps({'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'evidence_sha256': manifest, 'source_sha256': {str(Path(__file__).relative_to(ROOT)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}, indent=2) + '\n')
    # Supplement the report manifest's missing R146 pointer without overwriting
    # the report, initial manifest, or its frozen script/source hashes.
    supplement = ROOT / 'experiments/r157-tree-stage-summary/r146-evidence-supplement.json'
    target = ROOT / 'experiments/r146-tree-age-audit/evidence-provenance.json'
    if supplement.exists(): raise FileExistsError(supplement)
    supplement.write_text(json.dumps({'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'sha256': {str(target.relative_to(ROOT)): hashlib.sha256(target.read_bytes()).hexdigest()},
        'scope': 'Missing R146 evidence pointer supplement; historical files unchanged'}, indent=2) + '\n')
    print(json.dumps({'folder': str(folder.relative_to(ROOT)), 'records':len(records), 'scope':result['scope']}))


if __name__ == '__main__': main()
