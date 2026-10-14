import json
from pathlib import Path
import tempfile
import unittest

from context_governance.bundles import dependency_map, load_case, source_chunks
from context_governance.core import govern
from context_governance.quality import check_code
from context_governance.selftest_suite import build_suite


class TestEngineeringFixtures(unittest.TestCase):
    def test_deterministic_suite_and_stale_files_fail_before_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            suite=Path(temporary)
            build_suite(suite)
            before=(suite/'metadata'/'clamp.json').read_bytes()
            build_suite(suite)
            self.assertEqual((suite/'metadata'/'clamp.json').read_bytes(),before)
            root=suite/'repo_bundles'/'clamp'
            (root/'stale.py').write_text('old content')
            (root/'solution.py').write_text('preserve me')
            with self.assertRaisesRegex(ValueError,'unexpected/stale'): build_suite(suite)
            self.assertEqual((root/'solution.py').read_text(),'preserve me')

    def test_all_reference_files_pass_independent_oracles_and_bad_files_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            suite = Path(temporary)
            for case_id in build_suite(suite):
                metadata, root, spec, items = load_case(suite, case_id)
                test_file = suite / 'tests' / f'{case_id}.py'
                reference = (suite / 'oracle' / f'{case_id}.py').read_text()
                self.assertTrue(check_code(reference, root, 'solution.py', test_file)['passed'], case_id)
                self.assertFalse(check_code('pass', root, 'solution.py', test_file)['passed'], case_id)
                output = govern(spec, items, 3000)
                for item in items:
                    if item.protected: self.assertIn(item.text, output['context'])
                self.assertLess(output['metrics']['output_units'], output['metrics']['input_units'])
                (root / 'solution.py').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'checksum'): load_case(suite, case_id)

    def test_chunk_boundaries_preserve_decorators_and_imports(self):
        source = 'import math\n\n@decorate\ndef foo(x):\n    return math.sqrt(x)\n\ndef bar():\n    return 1\n'
        chunks = source_chunks('module.py', source)
        self.assertEqual(''.join(x.text for x in chunks), source)
        self.assertTrue(any('@decorate\ndef foo' in x.text for x in chunks))
        semicolons='import math; SCALE = 2\ndef calculate(x): return SCALE*math.sqrt(x)\n'
        chunks=source_chunks('helpers.py',semicolons)
        self.assertEqual(''.join(x.text for x in chunks),semicolons)
        self.assertEqual(len({x.id for x in chunks}),len(chunks))

    def test_source_dependencies_are_atomic_under_budget(self):
        text='import math\nSCALE=2\ndef calculate(x):\n    return SCALE*math.sqrt(x)\n'
        items=source_chunks('helpers.py',text)
        dependencies=dependency_map(items)
        output=govern('calculate',items,110,dependencies=dependencies)
        self.assertNotIn('def calculate',output['context'])
        output=govern('calculate',items,250,dependencies=dependencies)
        self.assertIn('SCALE=2',output['context'])
        self.assertIn('import math',output['context'])
        self.assertIn('def calculate',output['context'])

    def test_package_relative_and_star_import_closure(self):
        items=source_chunks('pkg/helpers.py','BASE=17\n')+source_chunks('pkg/__init__.py','from .helpers import BASE\n')+source_chunks('pkg/client.py','from .helpers import *\ndef fee(): return BASE\n')
        dependencies=dependency_map(items)
        output=govern('fee',items,500,dependencies=dependencies)
        self.assertIn('BASE=17',output['context'])
        fee_id=next(x.id for x in items if 'def fee' in x.text)
        self.assertIn('pkg/client.py:1-1',dependencies[fee_id])
        self.assertIn('pkg/helpers.py:1-1',dependencies['pkg/__init__.py:1-1'])

    def test_generated_file_guard_and_timeout_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); repo = root / 'repo'; repo.mkdir()
            (repo / 'solution.py').write_text('')
            test = root / 'test.py'; test.write_text('unittest.main()')
            self.assertFalse(check_code('import os\nos.system("bad")', repo, 'solution.py', test)['passed'])
            self.assertFalse(check_code('eval("42")', repo, 'solution.py', test)['passed'])

    def test_early_exit_cannot_pass_and_mutable_dependency_is_not_oracle(self):
        with tempfile.TemporaryDirectory() as temporary:
            suite=Path(temporary)
            build_suite(suite)
            metadata, root, _, _=load_case(suite,'shipping')
            tests=suite/'tests'/'shipping.py'
            self.assertFalse(check_code('raise SystemExit(0)',root,'solution.py',tests)['passed'])
            escaped='__builtins__["__import__"]("sys").exit(0)'
            self.assertFalse(check_code(escaped,root,'solution.py',tests)['passed'])
            polluted='import config\nconfig.BASE_FEE=config.PER_KG=config.FREE_FROM_KG=0\ndef shipping_fee(weight):\n    if weight<0: raise ValueError()\n    return 0\n'
            self.assertFalse(check_code(polluted,root,'solution.py',tests)['passed'])
            sabotage='import typing\ntyping.sys.modules["unittest"].TestCase.assertEqual=lambda *args: None\ndef shipping_fee(weight):\n    if weight<0: raise ValueError()\n    return 999\n'
            self.assertFalse(check_code(sabotage,root,'solution.py',tests)['passed'])


if __name__ == '__main__': unittest.main()
