"""Post-hoc reference audit; its results never enter model prompts or scores."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

from context_governance.bundles import load_case
from context_governance import public_examples as public_examples_module
from context_governance.public_examples import evaluate_examples
from context_governance.verify_recorded_eval import recorded_checker


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    parser.add_argument('--suite', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    path, suite, output = Path(args.report), Path(args.suite), Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    original_sha = sha(path)
    report = json.loads(path.read_text(encoding='utf-8'))
    if 'summary' not in report or not report.get('public_example_review'):
        raise ValueError('Require a completed public-example evaluation')
    if sha(suite / 'manifest.json') != report['suite_manifest_sha256']:
        raise ValueError('Suite manifest changed')
    public_module = Path(public_examples_module.__file__).resolve()
    expected_public = report['source_sha256_at_start']['public_examples.py']
    evaluator = evaluate_examples
    if sha(public_module) != expected_public:
        project = Path(__file__).resolve().parents[1]
        candidates = sorted((project / 'adapters').glob('research-v*-source/public_examples.py'))
        candidates += sorted((project / 'adapters').glob('research-v*/context_governance/public_examples.py'))
        matched = next((p for p in candidates if sha(p) == expected_public), None)
        if matched is None:
            raise ValueError('Matching frozen public-example template missing')
        public_module = matched
        module_spec = importlib.util.spec_from_file_location('context_governance._historical_public_audit', matched)
        historical = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = historical
        module_spec.loader.exec_module(historical)
        evaluator = historical.evaluate_examples
    checker, guard_sha = recorded_checker(report)
    started = time.time()
    results, unique = [], {}
    evidence = {
        'origin': 'Post-hoc audit of generated public tests against trusted local reference code',
        'scope': 'No model calls or score changes. Results were unavailable to every generation. '
                 'A reference rejection identifies disagreement with this local reference or its exact-equality tests; '
                 'it is not automatically proof of an incorrect public requirement. Identical case/response pairs '
                 'reuse one recorded audit execution only; this deduplication never changes timed model evaluation.',
        'started_unix': started, 'input_report_sha256': original_sha,
        'suite_manifest_sha256': sha(suite / 'manifest.json'),
        'script_sha256': sha(Path(__file__)), 'quality_guard_sha256': guard_sha,
        'public_examples_module_sha256': sha(public_module), 'cases': results,
    }
    for case in report['cases']:
        metadata, snapshot, spec, _ = load_case(suite, case['id'])
        if metadata['snapshot_sha256'] != case['snapshot_sha256']:
            raise ValueError('Case snapshot changed')
        reference_path = suite / 'oracle' / f"{case['id']}.py"
        reference = reference_path.read_text(encoding='utf-8')
        rows = []
        for mode, runs in case['runs'].items():
            for run in runs:
                response = run['public_examples_generation']['output']
                response_sha = hashlib.sha256(response.encode()).hexdigest()
                key = (case['id'], response_sha)
                reused = key in unique
                if not reused:
                    extra = ({'public_task': spec}
                             if report.get('public_examples_protocol') in ('public-contract-v21', 'public-contract-v22') else {})
                    unique[key] = evaluator(response, reference, snapshot,
                                                    metadata['target_file'], checker=checker, **extra)
                rows.append({'mode': mode, 'repeat': run['repeat'],
                             'response_sha256': response_sha, 'reused_identical_audit': reused,
                             'reference_public_result': unique[key],
                             'draft_public_result': run['public_examples_result']})
        results.append({'id': case['id'], 'reference_sha256': sha(reference_path), 'runs': rows})
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'case': case['id'], 'runs': len(rows),
                          'reference_rejected': sum(x['reference_public_result']['valid'] and
                                                    not x['reference_public_result']['passed'] for x in rows)}), flush=True)
    if sha(path) != original_sha:
        raise ValueError('Input report changed during audit')
    flat = [run for case in results for run in case['runs']]
    valid = [run for run in flat if run['reference_public_result']['valid']]
    evidence['summary'] = {
        'model_flows': len(flat), 'unique_case_response_audits': len(unique),
        'valid_example_flows': len(valid), 'protocol_rejected_flows': len(flat) - len(valid),
        'protocol_rejection_feedback_counts': dict(Counter(
            x['reference_public_result']['feedback'] for x in flat
            if not x['reference_public_result']['valid'])),
        'reference_accepted_flows': sum(x['reference_public_result']['passed'] for x in valid),
        'reference_rejected_flows': sum(not x['reference_public_result']['passed'] for x in valid),
        'scope': 'Counts are per recorded model flow, not independent test sets or model quality scores.',
    }
    evidence['finished_unix'] = time.time()
    evidence['wall_seconds'] = evidence['finished_unix'] - started
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(evidence['summary']), flush=True)


if __name__ == '__main__':
    main()
