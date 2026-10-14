"""Run trusted references using only the source modules present in context."""
import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path

from transformers import AutoTokenizer

from context_governance.bundles import load_case
from context_governance.core import govern
from context_governance.local_model import ModelTokenCounter
from context_governance.quality import check_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--suites', nargs='+', required=True)
    parser.add_argument('--budget', type=int, default=650)
    parser.add_argument('--output', default='artifacts/selected-dependency-audit-v13.json')
    args = parser.parse_args()
    model = Path(args.model)
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, trust_remote_code=False)
    counter = ModelTokenCounter(tokenizer)
    start = time.perf_counter()
    results = []
    for name in args.suites:
        suite = Path(name)
        manifest = json.loads((suite / 'manifest.json').read_text(encoding='utf-8'))
        for case_id in manifest['case_ids']:
            meta, original, spec, items = load_case(suite, case_id)
            selection = govern(spec, items, args.budget, counter, meta['context_dependencies'])
            selected_sources = {}
            for item in selection['selected']:
                if item['kind'] == 'code':
                    filename = item['id'].split(':')[0]
                    selected_sources.setdefault(filename, []).append(item['text'])
            with tempfile.TemporaryDirectory(prefix='hackathon11-selected-') as directory:
                root = Path(directory)
                for filename, pieces in selected_sources.items():
                    output = root / filename
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(''.join(pieces), encoding='utf-8')
                checked = check_code((suite / 'oracle' / f'{case_id}.py').read_text(encoding='utf-8'),
                                     root, meta['target_file'], suite / 'tests' / f'{case_id}.py')
            results.append({'suite': name, 'id': case_id, 'snapshot_sha256': meta['snapshot_sha256'],
                            'selected_code_ids': [item['id'] for item in selection['selected'] if item['kind'] == 'code'],
                            'selected_modules': sorted(selected_sources), 'tokens': selection['metrics']['output_units'],
                            'functional': checked})
            print(json.dumps({'id': case_id, 'passed': checked['passed']}), flush=True)
    report = {'origin': 'trusted reference dependency-closure audit; no model inference',
              'model_tokenizer': str(model.resolve()), 'budget': args.budget,
              'tokenizer_sha256': hashlib.sha256((model / 'tokenizer.json').read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'core_sha256': hashlib.sha256(Path(__import__('context_governance.core', fromlist=['core']).__file__).read_bytes()).hexdigest(),
              'cases': results, 'all_passed': all(x['functional']['passed'] for x in results),
              'wall_seconds': time.perf_counter() - start,
              'scope': 'Selected modules only plus trusted replacement of target file. Does not prove arbitrary dynamic dependency completeness.'}
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'cases': len(results), 'all_passed': report['all_passed'], 'wall_seconds': report['wall_seconds']}))
    if not report['all_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
