"""Model-environment controls for a real single-pass generation boundary."""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('transformers') and importlib.util.find_spec('torch'),
                     'optional model environment required')
class ReasoningBudgetTests(unittest.TestCase):
    def test_real_decoder_reuses_one_sequence_and_caps_answer_after_forced_boundary(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM,LogitsProcessorList,StoppingCriteriaList
        from context_governance.reasoning_budget import ReasoningBudget
        torch.set_num_threads(2)
        config=Qwen2Config(vocab_size=16,hidden_size=8,intermediate_size=16,num_hidden_layers=1,
            num_attention_heads=2,num_key_value_heads=1,max_position_embeddings=64,
            eos_token_id=15,pad_token_id=15)
        model=Qwen2ForCausalLM(config).eval()
        class One:
            def __call__(self,input_ids,scores):
                scores.fill_(-float('inf')); scores[:,1]=0; return scores
        control=ReasoningBudget(2,3,2)
        # A closing tag in the prompt must not disable the budget for the new answer.
        prompt=torch.tensor([[2,4,5]])
        with torch.inference_mode():
            ids=model.generate(input_ids=prompt,attention_mask=torch.ones_like(prompt),do_sample=False,
                max_new_tokens=20,logits_processor=LogitsProcessorList([One(),control]),
                stopping_criteria=StoppingCriteriaList([control.answer_limit_reached]))
        self.assertEqual(ids[0,3:].tolist(),[1,1,1,2,1,1])
        self.assertEqual(control.forced_positions,[3])
        self.assertEqual(control.closing_position,3)

    def test_natural_boundary_stays_untouched_and_duplicate_tokens_do_not_extend_budget(self):
        import torch
        from context_governance.reasoning_budget import ReasoningBudget
        control=ReasoningBudget(2,3,2)
        base=torch.tensor([[4,5]])
        scores=torch.zeros((1,16)); control(base,scores)
        seq=torch.tensor([[4,5,2]])
        self.assertFalse(control.answer_limit_reached(seq,None))
        self.assertTrue(torch.equal(control(seq,scores.clone()),scores))
        self.assertFalse(control.answer_limit_reached(torch.tensor([[4,5,2,2]]),None))
        self.assertTrue(control.answer_limit_reached(torch.tensor([[4,5,2,2,1]]),None))
        self.assertEqual(control.forced_positions,[])

    def test_public_model_api_records_control_and_refuses_answer_cap(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM,BatchEncoding
        from context_governance.local_model import LocalModel
        class Tokenizer:
            eos_token_id=15
            def __call__(self,prompt,return_tensors):
                ids=torch.tensor([[4,5]])
                return BatchEncoding({'input_ids':ids,'attention_mask':torch.ones_like(ids)})
            def decode(self,ids,skip_special_tokens):
                return ''.join('</think>' if int(x)==2 else 'x' for x in ids if not (skip_special_tokens and int(x)==15))
            def convert_tokens_to_ids(self,token): return 2
            def convert_ids_to_tokens(self,token): return '</think>' if token==2 else '?'
        config=Qwen2Config(vocab_size=16,hidden_size=8,intermediate_size=16,num_hidden_layers=1,
            num_attention_heads=2,num_key_value_heads=1,max_position_embeddings=64,eos_token_id=15,pad_token_id=15)
        owner=LocalModel.__new__(LocalModel)
        owner.torch=torch; owner.device='cpu'; owner.device_type='cpu'; owner.prefill_chunk=0
        owner.model=Qwen2ForCausalLM(config).eval(); owner.tokenizer=Tokenizer()
        owner.model.generation_config.suppress_tokens=[i for i in range(16) if i!=1]
        result=owner.generate_evidence('prompt',2,thinking=True,reasoning_budget=3)
        self.assertEqual(result['output_ids'],[1,1,1,2,1,1])
        self.assertEqual(result['forced_output_positions'],[3])
        self.assertEqual(result['decoding_passes'],1)
        self.assertEqual(result['sampled_output_tokens'],5)
        self.assertEqual(result['final_output'],'')
        self.assertIn('protocol_error',result)


if __name__=='__main__':unittest.main()
