import hashlib
from pathlib import Path
import tempfile
import unittest

from context_governance.quality import check_code
from context_governance.verify_recorded_eval import recorded_checker


class LibraryGuardTests(unittest.TestCase):
    def test_pure_copy_and_heapq_with_independent_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary); root=directory/'repo'; root.mkdir()
            (root/'solution.py').write_text('def run(values): pass',encoding='utf-8')
            test=directory/'checks.py'
            test.write_text('from solution import run\nclass Check(unittest.TestCase):\n'
                '    def test_clone_and_sort(self):\n'
                '        original={"nested":[3,1,2]}\n'
                '        copied,ordered=run(original)\n'
                '        copied["nested"].append(9)\n'
                '        self.assertEqual(original,{"nested":[3,1,2]})\n'
                '        self.assertEqual(ordered,[1,2,3])\n',encoding='utf-8')
            code='from copy import deepcopy\nfrom heapq import nsmallest\ndef run(values):\n    return deepcopy(values),nsmallest(3,values["nested"])\n'
            self.assertTrue(check_code(code,root,'solution.py',test)['passed'])
            historical=Path(__file__).resolve().parents[1]/'adapters'/'research-v17b-source'
            digest=hashlib.sha256((historical/'quality.py').read_bytes()).hexdigest()
            guard,pinned=recorded_checker({'source_sha256_at_start':{'quality.py':digest}})
            self.assertEqual(pinned,digest)
            self.assertEqual(guard(code,root,'solution.py',test)['reason'],'import outside fixture allowlist')

    def test_wrong_frozen_guard_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary); (path/'quality.py').write_text('raise RuntimeError("must not execute")')
            with self.assertRaises(ValueError):
                recorded_checker({'source_sha256_at_start':{'quality.py':'0'*64}},path)


if __name__=='__main__': unittest.main()
