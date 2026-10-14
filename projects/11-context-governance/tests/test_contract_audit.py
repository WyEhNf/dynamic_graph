import unittest
from context_governance.contract_audit import audit_draft


class TestPublicContractHints(unittest.TestCase):
    def test_identity_and_mutation_are_source_hints_without_execution(self):
        hints=audit_draft('Implement rotate(values). Return a new list. Do not modify values.',
                          'def rotate(values):\n    values.sort()\n    return values\n','')
        self.assertEqual(len(hints),2)
        copied=audit_draft('Implement rotate(values). Return a new list. Do not modify values.',
                          'def rotate(values):\n    values=values[:]\n    values.sort()\n    return values\n','')
        self.assertEqual(copied,[])
        self.assertEqual(audit_draft('Implement rotate(values). Return a new list.',
                         'def compatibility(value): return value\ndef rotate(values): return values[:]', ''),[])

    def test_missing_calls_and_required_exports_are_reported(self):
        spec='Implement normalized(x). Use validate from helpers.py. Preserve the existing VERSION constant unchanged.'
        draft='from helpers import validate\nVERSION=2\ndef normalized(x):\n    return x\n'
        original='VERSION=1\ndef normalized(x):\n    raise NotImplementedError\n'
        hints=audit_draft(spec,draft,original)
        self.assertTrue(any('no direct call' in hint for hint in hints))
        self.assertTrue(any('VERSION' in hint for hint in hints))
        self.assertEqual(audit_draft(spec,draft.replace('VERSION=2','VERSION=1').replace('return x','return validate(x)'),original),[])

    def test_syntax_and_exception_hints_do_not_claim_correctness(self):
        self.assertIn('syntax error',audit_draft('Implement f(x).','def f(', '')[0])
        self.assertIn('validation paths',audit_draft('Invalid values raise ValueError.','def f(x): return x','')[0])
        self.assertEqual(audit_draft('Implement f(x).','def f(x): return 999',''),[])
        caught=audit_draft('Invalid values must raise ValueError.',
              'def f(x):\n    try: return int(x)\n    except ValueError: return 0\n','')
        self.assertTrue(any('swallows' in hint for hint in caught))


if __name__=='__main__': unittest.main()
