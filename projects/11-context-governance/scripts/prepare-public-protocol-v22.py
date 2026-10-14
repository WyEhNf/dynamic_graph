"""Freeze a revision of v21's public contract after independent boundary review."""
import hashlib
import json
from pathlib import Path
import shutil
import time

root = Path(__file__).resolve().parents[1]
baseline = root / 'adapters/research-v21/context_governance'
destination = root / 'adapters/research-v22'
if destination.exists():
    raise FileExistsError(destination)
package = destination / 'context_governance'
package.mkdir(parents=True)
baseline_hashes = {}
for source in sorted(baseline.glob('*.py')):
    baseline_hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    shutil.copyfile(source, package / source.name)

public_path = package / 'public_examples.py'
public = public_path.read_text(encoding='utf-8').replace('import json\n', 'import json\nimport keyword\n', 1)
start = public.index('def declared_functions(')
end = public.index('\n\ndef parse_examples(', start)
public = public[:start] + '''def declared_functions(target_source, public_task=None):
    functions = {n.name for n in ast.parse(target_source).body
                 if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')}
    if public_task is not None:
        # An explicit required API takes precedence over pre-existing helpers.
        # Keep this same allowlist in the prompt and trusted example parser.
        names = re.findall(r'(?m)^\\s*Implement\\s+([A-Za-z_]\\w*)\\s*\\(', public_task)
        if names:
            return {name for name in names if name.isidentifier()
                    and not keyword.iskeyword(name) and not name.startswith('_')}
    return functions
''' + public[end:]
public_path.write_text(public, encoding='utf-8')

local_path = package / 'local_model.py'
local = local_path.read_text(encoding='utf-8')
old = """            names = sorted(declared_functions(target_source, task))
            declarations = re.findall(r'(?m)^\\s*Implement\\s+([A-Za-z_]\\w*)\\s*\\([^)]*\\)', task)
            required = [name for name in declarations if name in names]
            allowed = required or names"""
assert local.count(old) == 1
local = local.replace(old, '            allowed = sorted(declared_functions(target_source, task))')
local_path.write_text(local, encoding='utf-8')
for name in ('local_model.py', 'run_local_eval.py', 'verify_recorded_eval.py'):
    path = package / name
    text = path.read_text(encoding='utf-8')
    assert 'public-contract-v21' in text
    path.write_text(text.replace('public-contract-v21', 'public-contract-v22'), encoding='utf-8')

test = (root / 'adapters/research-v21/test_public_contract.py').read_text(encoding='utf-8')
test = test.replace('public-contract-compatibility-v21.json', 'public-contract-compatibility-v22.json')
test = test.replace("if __name__ == '__main__':", """class ReviewedBoundaryTests(unittest.TestCase):
    def test_required_api_excludes_preexisting_helper_in_both_prompt_and_parser(self):
        target = 'def legacy_helper(x): return x\\n'
        task = 'Implement new_api(x).'
        response = json.dumps([{'function': 'legacy_helper', 'args_python': '[3]', 'expected_python': '3'}])
        with self.assertRaises(ValueError):
            parse_examples(response, target, task)
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs): return messages
        prompt = LocalModel.examples_prompt(SimpleNamespace(tokenizer=Tokenizer()), '', task, target, 'public-contract-v22')
        self.assertTrue(prompt[1]['content'].startswith('ALLOWED FUNCTION NAMES: [\"new_api\"]'))

    def test_keyword_function_is_rejected_before_trusted_template(self):
        with tempfile.TemporaryDirectory() as name:
            snapshot = Path(name)
            (snapshot / 'solution.py').write_text('# Placeholder\\n', encoding='utf-8')
            response = json.dumps([{'function': 'class', 'args_python': '[3]', 'expected_python': '3'}])
            result = evaluate_examples(response, 'def valid(x): return x\\n', snapshot, 'solution.py', public_task='Implement class(x).')
            self.assertFalse(result['valid'])
            self.assertIsNone(result['test_sha256'])


if __name__ == '__main__':""")
test = test.replace('unittest.defaultTestLoader.loadTestsFromTestCase(PublicContractTests)])',
                    'unittest.defaultTestLoader.loadTestsFromTestCase(PublicContractTests),\n                               unittest.defaultTestLoader.loadTestsFromTestCase(ReviewedBoundaryTests)])')
test = test.replace('plus four public-contract integration regressions.', 'plus four public-contract integration regressions and two independently identified API boundary regressions.')
(destination / 'test_public_contract.py').write_text(test, encoding='utf-8')
provenance = {'prepared_unix': time.time(), 'baseline': str(baseline),
              'baseline_module_sha256': baseline_hashes,
              'candidate_module_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.glob('*.py'))},
              'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'changes': 'Public-task required API takes precedence over old helpers; Python keywords fail closed; prompt/parser share the same allowlist; literal-v17 unchanged.',
              'scope': 'Isolated candidate. No active Python source, dataset, model or hidden evaluator was changed.'}
(destination / 'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
print(json.dumps({'candidate': str(destination), 'modules': len(baseline_hashes)}))
