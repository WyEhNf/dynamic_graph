import json
from pathlib import Path
import tempfile
import unittest

from context_governance.public_examples import evaluate_examples, parse_examples


class PublicExampleTests(unittest.TestCase):
    source = 'def double(x):\n    raise NotImplementedError\n'

    def example(self, **updates):
        result = {'function':'double', 'args_python':'(3,)', 'expected_python':'6'}
        result.update(updates)
        return json.dumps([result])

    def test_expressions_and_oversized_literals_rejected(self):
        for argument in ('(__import__("os").system("echo bad"),)', '(2**1024,)',
                         '('+'['*18+'0'+']'*18+',)', '(1e309,)', '('+'1'+ '0'*100+',)'):
            with self.subTest(argument=argument):
                with self.assertRaises((ValueError,SyntaxError)):
                    parse_examples(self.example(args_python=argument),self.source)
        with self.assertRaises(ValueError):
            parse_examples(self.example(expected_python="'"+'x'*4097+"'"),self.source)

    def test_target_scope_and_exact_schema(self):
        for updates in ({'function':'system'}, {'function':'__import__'}, {'extra':1}, {'args_python':'[3]'}):
            with self.assertRaises(ValueError):
                parse_examples(self.example(**updates),self.source)
        with self.assertRaises(ValueError):
            parse_examples('[]',self.source)
        entries,parsed=parse_examples(self.example(args_python='({3, 2},)',expected_python='{2, 3}'),self.source)
        self.assertEqual(parsed[0]['args_source'],'({3, 2},)')

    def test_guarded_execution_and_stable_feedback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); (root/'solution.py').write_text(self.source,encoding='utf-8')
            draft='def double(x):\n    return x*2\n'
            good=evaluate_examples(self.example(args_python='(3,) # trailing comment'),draft,root,'solution.py')
            self.assertTrue(good['passed']); self.assertEqual(good['outcomes'],['ok'])
            wrong=self.example(expected_python='7')
            first=evaluate_examples(wrong,draft,root,'solution.py')
            second=evaluate_examples(wrong,draft,root,'solution.py')
            self.assertFalse(first['passed']); self.assertEqual(first,second)
            self.assertEqual(first['outcomes'],['FAIL'])
            self.assertNotIn(temporary,first['feedback'])
            unsafe=evaluate_examples(self.example(),'import os\ndef double(x): return 6',root,'solution.py')
            self.assertFalse(unsafe['passed']); self.assertEqual(unsafe['outcomes'],['not completed'])

    def test_expected_exception_and_malformed_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); (root/'solution.py').write_text(self.source,encoding='utf-8')
            response=json.dumps([{'function':'double','args_python':'(-1,)','raises':'ValueError'}])
            result=evaluate_examples(response,'def double(x):\n    raise ValueError("negative")',root,'solution.py')
            self.assertTrue(result['passed'])
            malformed=evaluate_examples('not JSON','def double(x): return x',root,'solution.py')
            self.assertFalse(malformed['valid']); self.assertIsNone(malformed['test_sha256'])


if __name__=='__main__': unittest.main()
