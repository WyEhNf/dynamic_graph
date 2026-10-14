"""Read a completed public-feedback batch without rerunning or changing it."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, target = Path(args.report), Path(args.output)
    if target.exists():
        raise FileExistsError(target)
    report = json.loads(source.read_text(encoding='utf-8'))
    if 'summary' not in report or len(report['cases']) != 30:
        raise ValueError('Require the completed fixed 30-task development batch')
    groups = {}
    for name, start, end in [('original20', 0, 20), ('structural6', 20, 26), ('workflow4', 26, 30), ('all30', 0, 30)]:
        cases = report['cases'][start:end]
        group = {'tasks': len(cases), 'modes': {}}
        for mode in ('baseline', 'compressed'):
            runs = [r for c in cases for r in c['runs'][mode]]
            valid = [r for r in runs if r['public_examples_result']['valid']]
            group['modes'][mode] = {
                'flows': len(runs),
                'all_repeats_passed_tasks': sum(all(r['functional']['passed'] for r in c['runs'][mode]) for c in cases),
                'all_repeats_draft_passed_tasks': sum(all(r['draft_functional']['passed'] for r in c['runs'][mode]) for c in cases),
                'passed_final_flows': sum(r['functional']['passed'] for r in runs),
                'valid_public_example_flows': len(valid),
                'protocol_rejected_flows': len(runs) - len(valid),
                'protocol_rejection_counts': dict(Counter(r['public_examples_result']['feedback'] for r in runs if not r['public_examples_result']['valid'])),
                'draft_to_final_regressions': [{'case': c['id'], 'repeat': r['repeat']} for c in cases for r in c['runs'][mode] if r['draft_functional']['passed'] and not r['functional']['passed']],
                'failed_final_cases': [c['id'] for c in cases if not all(r['functional']['passed'] for r in c['runs'][mode])],
            }
        groups[name] = group
    result = {'origin': 'Read-only subgroup analysis of a completed batch',
              'scope': 'Existing 20+6+4 development tasks; no new holdout or model execution. One-repeat batches do not establish repeat stability.',
              'report_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'report_summary': report['summary'], 'groups': groups}
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
