"""Join frozen quality and audited necessary floors by original input SHA."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'experiments/r124-copy-opportunities'; folder.mkdir(exist_ok=False)
    sources = [('r107-age-portfolio-336', 'r99-reduction-global-audit'),
               ('r108-age-portfolio-heldout', 'r123-age-holdout-floor')]
    stages = {}; source_hashes = {}
    for quality, floor in sources:
        quality_path = ROOT / 'experiments' / quality / 'report.json'
        floor_path = ROOT / 'experiments' / floor / 'report.json'
        report = json.loads(quality_path.read_text()); lower = json.loads(floor_path.read_text())
        bounds = {row['sha256']: row for row in lower['records']}
        records = []
        for row in report['records']:
            if row['variant'] != report['paired_variants']['after']: continue
            item = {key: row[key] for key in ('sha256', 'family', 'seed', 'node_count', 'bit_width', 'status')}
            floor_row = bounds[row['sha256']]; item['copy_lower_bound'] = floor_row['copy_lower_bound']
            item['certificate_kinds'] = [entry['certificate']['kind'] for entry in floor_row['proofs']]
            if row['status'] == 'verified':
                copies = row['inserted_copies']; count = row['node_count']; bound = item['copy_lower_bound']
                assert copies >= bound
                item.update(copies=copies, potential_copy_reduction_upper_bound=copies - bound,
                    copy_per_output=copies / (count + copies), lower_copy_per_output=bound / (count + bound),
                    percentage_point_upper_bound=100 * (copies / (count + copies) - bound / (count + bound)))
            records.append(item)
        assert len(records) == report['case_count'] == len(bounds)
        groups = defaultdict(list)
        for row in records: groups[row['family']].append(row)
        summaries = {}
        for family, rows in groups.items():
            complete = [row for row in rows if row['status'] == 'verified']
            summaries[family] = {'count': len(rows), 'statuses': dict(Counter(row['status'] for row in rows)),
                'copies': sum(row['copies'] for row in complete),
                'necessary_copy_floor_successes': sum(row['copy_lower_bound'] for row in complete),
                'potential_copy_reduction_upper_bound': sum(row['potential_copy_reduction_upper_bound'] for row in complete),
                'whole_input_mean_percentage_point_upper_bound_contribution': sum(row['percentage_point_upper_bound'] for row in complete) / len(records)}
        stages[quality] = {'count': len(records), 'statuses': dict(Counter(row['status'] for row in records)),
            'floor_source': floor, 'families': summaries, 'records': records,
            'largest_absolute_gaps': sorted((row for row in records if row['status'] == 'verified'),
                key=lambda row: row['potential_copy_reduction_upper_bound'], reverse=True)[:30]}
        for path in (quality_path, floor_path): source_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'sources_sha256': source_hashes,
        'scope': 'All336 and72 original inputs retained; only measured legal outputs have actual gap. '
                 'C-L is an UPPER bound on remaining achievable COPY reduction, not attainable target; '
                 'L=0 may be weak; no whole-input score supplied where outputs absent; no official Level claim', 'stages': stages}
    (folder / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    for stage, data in stages.items():
        print(json.dumps({'stage': stage, 'count': data['count'], 'statuses': data['statuses'],
                          'families': data['families']}, ensure_ascii=False))


if __name__ == '__main__': main()
