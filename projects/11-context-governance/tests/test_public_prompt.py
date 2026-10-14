import unittest
from context_governance.public_prompt import candidate_messages


class PublicPromptTests(unittest.TestCase):
    def test_initial_never_includes_repair_evidence(self):
        messages=candidate_messages('CTX','REQ',public_tests='TEST_SENTINEL',feedback='ERROR_SENTINEL')
        self.assertEqual([m['role'] for m in messages],['system','user'])
        self.assertNotIn('TEST_SENTINEL',str(messages))
        self.assertNotIn('ERROR_SENTINEL',str(messages))

    def test_repair_preserves_assistant_boundary_and_repeats_contract_last(self):
        messages=candidate_messages('CTX','REQ',previous='DRAFT',public_tests='TEST',feedback='ERROR')
        self.assertEqual([m['role'] for m in messages],['system','user','assistant','user'])
        self.assertEqual(messages[2]['content'],'DRAFT')
        final=messages[-1]['content']
        self.assertLess(final.index('TEST'),final.index('ERROR'))
        self.assertLess(final.index('ERROR'),final.index('REQ'))
        self.assertIn('complete corrected target',final)


if __name__=='__main__':unittest.main()
