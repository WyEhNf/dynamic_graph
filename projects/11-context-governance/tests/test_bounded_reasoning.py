import unittest
from context_governance.bounded_reasoning import generate_bounded_reasoning


class Tokenizer:
    def encode(self,text,add_special_tokens): return list(text)
    def convert_tokens_to_ids(self,text): return 2


def segment(text,ids,eos=False):
    return {'output':text,'raw_output':text,'output_ids':ids,'input_tokens':10,
            'output_tokens':len(ids),'ttft_ms':1,'elapsed_ms':2,'stopped_on_eos':eos,
            'final_output':text if eos else '', **({} if eos else {'protocol_error':'no EOS'})}


class BoundedReasoningTests(unittest.TestCase):
    def run_segments(self,segments):
        prompts=[]
        def generate(prompt,budget,**kwargs): prompts.append(prompt); return segments[len(prompts)-1]
        result=generate_bounded_reasoning(generate,Tokenizer(),'PROMPT',reasoning_budget=2,answer_budget=8)
        return result,prompts

    def test_forced_control_is_explicit_and_final_only_contains_completion(self):
        result,prompts=self.run_segments([segment('analysis with draft code',[1,1]),segment('```python\nanswer()\n```',[3,9],True)])
        self.assertTrue(result['forced_reasoning_end'])
        self.assertEqual(result['final_output'],'```python\nanswer()\n```')
        self.assertEqual(result['output_tokens'],4)
        self.assertEqual(result['input_tokens'],20)
        self.assertEqual(result['reasoning_tokens'],2)
        self.assertIn('</think>',prompts[1])
        self.assertIn('protocol_error',result['segments'][0])
        self.assertNotIn('protocol_error',result)

    def test_natural_boundary_preserves_partial_final_file(self):
        result,_=self.run_segments([segment('analysis</think>```python\ndef ',[1,2,3]),segment('answer(): pass\n```',[4,9],True)])
        self.assertFalse(result['forced_reasoning_end'])
        self.assertEqual(result['final_output'],'```python\ndef answer(): pass\n```')
        self.assertEqual(result['reasoning_tokens'],2)

    def test_finished_first_stage_needs_no_second_stage(self):
        first=segment('analysis</think>answer',[1,2,3,9],True)
        result,prompts=self.run_segments([first])
        self.assertEqual(len(prompts),1)
        self.assertFalse(result['forced_reasoning_end'])

    def test_missing_final_eos_and_new_thinking_are_rejected(self):
        for second in (segment('partial',[3]),segment('<think>restart</think>answer',[3,9],True)):
            result,_=self.run_segments([segment('analysis',[1,1]),second])
            self.assertIn('protocol_error',result)
            self.assertEqual(result['final_output'],'')


if __name__=='__main__':unittest.main()
