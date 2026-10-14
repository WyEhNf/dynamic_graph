"""Static hash-joined JSON aggregation only; no scheduling/proof search."""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'experiments/r143-root-lifetime-summary'; folder.mkdir(exist_ok=False)
    old_path = ROOT / 'experiments/r99-reduction-global-audit/report.json'
    new_path = ROOT / 'experiments/r134-root-potential-336/report.json'
    quality_path = ROOT / 'experiments/r107-age-portfolio-336/report.json'
    old = {row['sha256']: row for row in json.loads(old_path.read_text())['records']}
    new = {row['sha256']: row for row in json.loads(new_path.read_text())['records']}
    quality = json.loads(quality_path.read_text()); after = quality['paired_variants']['after']
    measured = {row['sha256']: row for row in quality['records'] if row['variant'] == after}
    assert old.keys() == new.keys() == measured.keys()
    joined = []
    for key, row in new.items():
        item = {'sha256': key, 'family': row['family'], 'node_count': row['node_count'],
                'bit_width': row['bit_width'], 'quality_status': measured[key]['status'],
                'old_lower': old[key]['copy_lower_bound'], 'root_lower': row['lower']}
        item['joint_lower'] = max(item['old_lower'], item['root_lower'])
        if measured[key]['status'] == 'verified':
            item['copies'] = measured[key]['inserted_copies']; assert item['joint_lower'] <= item['copies']
            item['gap_upper'] = item['copies'] - item['joint_lower']
        joined.append(item)
    def summary(rows):
        return {'count': len(rows), 'statuses': dict(Counter(row['quality_status'] for row in rows)),
                'old_mean_lower_output_pct': float(sum((Fraction(row['old_lower'], row['node_count'] + row['old_lower']) for row in rows), Fraction()) / len(rows) * 100),
                'joint_mean_lower_output_pct': float(sum((Fraction(row['joint_lower'], row['node_count'] + row['joint_lower']) for row in rows), Fraction()) / len(rows) * 100),
                'joint_mean_lower_original_pct': float(sum((Fraction(row['joint_lower'], row['node_count']) for row in rows), Fraction()) / len(rows) * 100),
                'lower_improved_inputs': sum(row['joint_lower'] > row['old_lower'] for row in rows)}
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'all336_necessary_only': summary(joined),
              'measured272_necessary_only': summary([row for row in joined if row['quality_status'] == 'verified']),
              'records': joined, 'sources_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                                   for path in (old_path, new_path, quality_path)},
              'scope': 'Necessary bounds in frozen strict model, all336 kept including47 impossible identities. 272 is explicit subset; no actual COPY reduction or official Level verdict. Original online/default quality untouched.'}
    pairs = {}
    for name, sources in [('old16', ['r138-spine-lifetime-cross', 'r140-spine-lifetime-macro-cross']),
                          ('new16', ['r139-spine-lifetime-heldout', 'r141-spine-lifetime-macro-heldout'])]:
        variants = [json.loads((ROOT / 'experiments' / source / 'report.json').read_text()) for source in sources]
        bank = [{row['sha256']: row for row in variant['records']} for variant in variants]
        assert bank[0].keys() == bank[1].keys(); combined = []
        for key in bank[0]:
            a, b = bank[0][key], bank[1][key]
            assert a['before_copies'] == b['before_copies'] and a['before_status'] == b['before_status']
            counts = [row['after_copies'] for row in (a, b) if row['after_copies'] is not None]
            combined.append({'sha256': key, 'before_copies': a['before_copies'], 'best_saved_copies': min(counts) if counts else None,
                             'status': a['after_status'], 'sources': sources})
        pairs[name] = {'count': len(combined), 'statuses': dict(Counter(row['status'] for row in combined)),
                       'before_copies': sum(row['before_copies'] or 0 for row in combined),
                       'best_saved_copies': sum(row['best_saved_copies'] or 0 for row in combined),
                       'rows': combined, 'scope': 'Offline min of two separately measured candidates, not a new single-budget online benchmark'}
    result['saved_candidate_bank'] = pairs
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('records', 'sources_sha256', 'saved_candidate_bank')}))
    print(json.dumps({key: {k: v for k, v in row.items() if k != 'rows'} for key, row in pairs.items()}))


if __name__ == '__main__': main()
