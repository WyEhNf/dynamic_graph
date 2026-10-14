"""Targeted protocol regression; no model inference or hidden task feedback."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest

directory = Path(__file__).resolve().parent
root = directory.parents[1]
sys.path.insert(0, str(directory))
sys.path.append(str(root / 'tests'))
from context_governance.local_model import LocalModel
from context_governance.public_examples import evaluate_examples, parse_examples


class PublicContractTests(unittest.TestCase):
    def test_new_function_placeholder_and_legacy_rejection(self):
        response = json.dumps([{'function': 'double', 'args_python': '[3]', 'expected_python': '6'}])
        with tempfile.TemporaryDirectory() as name:
            snapshot = Path(name)
            (snapshot / 'solution.py').write_text('# Implement the task here.\n', encoding='utf-8')
            draft = 'def double(x):\n    return x * 2\n'
            legacy = evaluate_examples(response, draft, snapshot, 'solution.py')
            self.assertFalse(legacy['valid'])
            current = evaluate_examples(response, draft, snapshot, 'solution.py',
                                        public_task='Implement double(x). Return twice x.')
            self.assertTrue(current['valid'])
            self.assertTrue(current['passed'])
            self.assertEqual(current['outcomes'], ['ok'])

    def test_public_declaration_does_not_enable_undeclared_or_private_calls(self):
        for name, task in [('system', 'Implement double(x).'),
                           ('__import__', 'Implement __import__(x).'),
                           ('system', 'A comment says Implement system(x), but no API declaration.')]:
            response = json.dumps([{'function': name, 'args_python': '[3]', 'expected_python': '6'}])
            with self.subTest(name=name, task=task), self.assertRaises(ValueError):
                parse_examples(response, '# No implementation yet.\n', task)
        with self.assertRaises(ValueError):
            parse_examples(json.dumps([{'function': 'double', 'args_python': '[__import__("os")]',
                                        'expected_python': '6'}]), '# Placeholder\n', 'Implement double(x).')

    def test_nested_list_arguments_preserve_tuple_expected_type(self):
        response = json.dumps([{'function': 'double', 'args_python': '[[1, 3]]',
                                'expected_python': '([2, 6], 2)'}])
        with tempfile.TemporaryDirectory() as name:
            snapshot = Path(name)
            (snapshot / 'solution.py').write_text('# Placeholder\n', encoding='utf-8')
            result = evaluate_examples(response, 'def double(xs):\n    return ([x*2 for x in xs], len(xs))\n',
                                       snapshot, 'solution.py', public_task='Implement double(xs).')
            self.assertTrue(result['passed'])

    def test_literal_v17_prompt_remains_byte_identical(self):
        path = root / 'adapters/research-v17d-source/local_model.py'
        spec = importlib.util.spec_from_file_location('context_governance._old_prompt_contract', path)
        legacy = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = legacy
        spec.loader.exec_module(legacy)
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return json.dumps({'messages': messages, 'options': kwargs}, ensure_ascii=False)
        owner = SimpleNamespace(tokenizer=Tokenizer())
        for context, task in [('def helper(x): return x\n', 'Implement double(x).'),
                              ('# 文件\r\n', 'Implement patch_text(text, edits). Validate all edits.')]:
            self.assertEqual(legacy.LocalModel.examples_prompt(owner, context, task),
                             LocalModel.examples_prompt(owner, context, task, '# Ignored in legacy\n', 'literal-v17'))


class ReviewedBoundaryTests(unittest.TestCase):
    def test_required_api_excludes_preexisting_helper_in_both_prompt_and_parser(self):
        target = 'def legacy_helper(x): return x\n'
        task = 'Implement new_api(x).'
        response = json.dumps([{'function': 'legacy_helper', 'args_python': '[3]', 'expected_python': '3'}])
        with self.assertRaises(ValueError):
            parse_examples(response, target, task)
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs): return messages
        prompt = LocalModel.examples_prompt(SimpleNamespace(tokenizer=Tokenizer()), '', task, target, 'public-contract-v22')
        self.assertTrue(prompt[1]['content'].startswith('ALLOWED FUNCTION NAMES: ["new_api"]'))

    def test_keyword_function_is_rejected_before_trusted_template(self):
        with tempfile.TemporaryDirectory() as name:
            snapshot = Path(name)
            (snapshot / 'solution.py').write_text('# Placeholder\n', encoding='utf-8')
            response = json.dumps([{'function': 'class', 'args_python': '[3]', 'expected_python': '3'}])
            result = evaluate_examples(response, 'def valid(x): return x\n', snapshot, 'solution.py', public_task='Implement class(x).')
            self.assertFalse(result['valid'])
            self.assertIsNone(result['test_sha256'])


if __name__ == '__main__':
    output = root / 'artifacts/public-contract-compatibility-v22.json'
    if output.exists():
        raise FileExistsError(output)
    started = time.perf_counter()
    source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (directory / 'context_governance').glob('*.py')}
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromName('test_public_examples'),
                               unittest.defaultTestLoader.loadTestsFromTestCase(PublicContractTests),
                               unittest.defaultTestLoader.loadTestsFromTestCase(ReviewedBoundaryTests)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'successful': result.wasSuccessful(),
              'wall_seconds': time.perf_counter()-started, 'candidate_module_sha256': source,
              'test_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'legacy_test_sha256': hashlib.sha256((root / 'tests/test_public_examples.py').read_bytes()).hexdigest(),
              'scope': 'Four unchanged literal-v17 safety/execution tests plus four public-contract integration regressions and two independently identified API boundary regressions. '
                       'No model calls, generated-example reliability or engineering code-quality conclusion.'}
    output.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if 'sha256' not in k}))
    if not result.wasSuccessful():
        raise SystemExit(1)
