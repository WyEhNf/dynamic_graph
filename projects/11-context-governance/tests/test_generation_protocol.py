import unittest
from context_governance.local_model import Generation
from context_governance.generation_protocol import generation_record, validate_sampling


class Tokens:
    words = {1: 'draft ```python\nwrong()\n```', 2: '</think>', 3: '```python\nright()\n```', 9: '<eos>'}
    def decode(self, ids, skip_special_tokens):
        return ''.join(self.words[i] for i in ids if not (skip_special_tokens and i == 9))
    def convert_tokens_to_ids(self, token): return 2 if token == '</think>' else -1


class GenerationProtocolTests(unittest.TestCase):
    def record(self, ids, thinking=True):
        return generation_record(Generation('', 1, 2, 3, len(ids)), ids, Tokens(), [9, 10], thinking=thinking)

    def test_final_code_is_after_reasoning_and_requires_eos(self):
        result=self.record([1, 2, 3, 9])
        self.assertEqual(result['final_output'], '```python\nright()\n```')
        self.assertEqual(result['reasoning_tokens'], 2)
        self.assertEqual(result['output_ids'], [1, 2, 3, 9])
        self.assertNotIn('protocol_error', result)

    def test_cap_timeout_missing_boundary_duplicate_boundary_empty_rejected(self):
        for ids in ([1, 2, 3], [1, 9], [1, 2, 2, 3, 9], [1, 2, 9]):
            with self.subTest(ids=ids):
                result=self.record(ids)
                self.assertIn('protocol_error', result)
                self.assertEqual(result['final_output'], '')

    def test_nonreasoning_does_not_need_boundary_but_refuses_stray_reasoning(self):
        self.assertNotIn('protocol_error', self.record([3, 9], False))
        self.assertIn('protocol_error', self.record([1, 2, 3, 9], False))

    def test_sampling_rejects_nonfinite_ambiguous_and_unsafe_options(self):
        valid={'temperature':.6, 'top_p':.95, 'top_k':20}
        self.assertEqual(validate_sampling(valid), {'do_sample':True, **valid})
        self.assertEqual(validate_sampling(None), {'do_sample':False})
        for value in ({}, {**valid, 'temperature':float('nan')}, {**valid, 'top_p':0},
                      {**valid, 'top_k':True}, {**valid, 'logits_processor':object()}):
            with self.assertRaises(ValueError): validate_sampling(value)


if __name__=='__main__': unittest.main()
