"""Optional model-environment test: causal cache equivalence, no GPU/download."""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('transformers') and importlib.util.find_spec('torch'),
                     'optional model dependencies are not in the core environment')
class TestChunkedPrefill(unittest.TestCase):
    def test_first_token_logits_and_generation_match_unsplit_prompt(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM,BatchEncoding
        from context_governance.local_model import LocalModel
        class Tokenizer:
            eos_token_id=63
            def __call__(self,prompt,return_tensors):
                ids=torch.tensor([[1+(ord(x)%61) for x in prompt]])
                return BatchEncoding({'input_ids':ids,'attention_mask':torch.ones_like(ids)})
            def decode(self,ids,skip_special_tokens): return ','.join(str(int(x)) for x in ids if x!=63)
        torch.manual_seed(1135); torch.set_num_threads(2)
        config=Qwen2Config(vocab_size=64,hidden_size=16,intermediate_size=32,num_hidden_layers=2,
                          num_attention_heads=2,num_key_value_heads=1,max_position_embeddings=512,
                          bos_token_id=62,eos_token_id=63,pad_token_id=63)
        owner=LocalModel.__new__(LocalModel)
        owner.torch=torch; owner.device='cpu'; owner.device_type='cpu'; owner.tokenizer=Tokenizer()
        owner.model=Qwen2ForCausalLM(config).eval(); owner.prefill_chunk=0
        records=[]
        def capture(module,args,kwargs,output):
            records.append((kwargs['input_ids'].shape[1],output.logits[:,-1,:].detach().clone()))
        hook=owner.model.register_forward_hook(capture,with_kwargs=True)
        prompt='abcdefghijklmnopqrstuvwxyz01234567890'
        native=owner.generate(prompt,5); first_logits=records[0][1]; records.clear()
        owner.prefill_chunk=7
        chunked=owner.generate(prompt,5)
        # The first prefill chunks sum to 30 and generate receives the final 7.
        prefix_calls=next(i for i in range(len(records)) if sum(x[0] for x in records[:i+1])==len(prompt))
        torch.testing.assert_close(records[prefix_calls][1],first_logits,rtol=1e-5,atol=1e-7)
        self.assertEqual(native.output,chunked.output)
        self.assertEqual(native.input_tokens,len(prompt)); self.assertEqual(chunked.input_tokens,len(prompt))
        self.assertGreater(chunked.ttft_ms,0)
        hook.remove()
        evidence=owner.generate_evidence(prompt,5)
        self.assertEqual(evidence['output'],chunked.output)
        self.assertEqual(evidence['output_tokens'],len(evidence['output_ids']))
        self.assertEqual(evidence['stopped_on_eos'],evidence['output_ids'][-1]==63)
        limited=owner.generate_evidence(prompt,100,max_seconds=0.000001)
        self.assertLess(limited['output_tokens'],100)
        if not limited['stopped_on_eos']:
            self.assertEqual(limited['final_output'],'')
            self.assertIn('protocol_error',limited)


if __name__=='__main__': unittest.main()
