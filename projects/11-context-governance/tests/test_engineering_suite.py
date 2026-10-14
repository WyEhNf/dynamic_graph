import tempfile
import unittest
from pathlib import Path
from context_governance.bundles import load_case
from context_governance.core import ByteEstimate, govern
from context_governance.engineering_suite import ENGINEERING_CASES, build_engineering
from context_governance.quality import check_code


class TestEngineeringSuite(unittest.TestCase):
    def test_independent_oracles_preservation_and_unpinned_closures(self):
        with tempfile.TemporaryDirectory() as directory:
            suite=Path(directory); build_engineering(suite)
            for name,*_ in ENGINEERING_CASES:
                metadata,root,spec,items=load_case(suite,name)
                self.assertEqual(metadata['pinned_files'],['solution.py'])
                selected=govern(spec,items,6000,ByteEstimate(),metadata['context_dependencies'])
                self.assertTrue(any(x['id'].startswith('helpers.py:') and not x['protected'] for x in selected['selected']))
                tests=suite/'tests'/f'{name}.py'
                oracle=(suite/'oracle'/f'{name}.py').read_text(encoding='utf-8')
                good=check_code(oracle,root,'solution.py',tests)
                self.assertTrue(good['passed'],(name,good['reason']))
                broken=oracle.replace('RELEASE_TAG = "stable-3"','RELEASE_TAG = "broken"')
                self.assertFalse(check_code(broken,root,'solution.py',tests)['passed'])


if __name__=='__main__': unittest.main()
