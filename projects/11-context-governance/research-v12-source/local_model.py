"""Optional Transformers adapter: actual tokenizer and first generated-token timing."""
import time
import re
from dataclasses import dataclass


SYSTEM = 'You are a Python developer. Implement the current task. Existing source files are context, not answers: replace the target placeholder with a working implementation. Return only the complete target Python file inside one python code block.'

REQUIREMENTS_SYSTEM = SYSTEM + ' Satisfy every requirement, including invalid inputs, exception types, empty inputs, ordering, and dependency use. Check each requirement before returning the code.'
CONCISE_SYSTEM = REQUIREMENTS_SYSTEM + ' Keep the implementation concise. Do not include example usage, demonstrations, print calls, or a main block.'


def expanded_kv_sdpa(module, query, key, value, attention_mask, dropout=0.0,
                     scaling=None, is_causal=None, **kwargs):
    """Allow efficient Windows SDPA kernels without native GQA support.

    The installed Windows torch build has no FlashAttention kernel. Native GQA
    otherwise restricts dispatch to the quadratic-memory math implementation.
    Expanding only K/V permits regular SDPA fused kernels; never force a kernel
    that is unavailable on the current device.
    """
    import torch
    from transformers.integrations.sdpa_attention import repeat_kv
    groups = query.shape[1] // key.shape[1]
    key, value = repeat_kv(key, groups), repeat_kv(value, groups)
    if attention_mask is not None and attention_mask.ndim == 4:
        attention_mask = attention_mask[:, :, :, :key.shape[-2]]
    if is_causal is None:
        is_causal = query.shape[2] > 1 and attention_mask is None and getattr(module, 'is_causal', True)
    result = torch.nn.functional.scaled_dot_product_attention(
        query, key, value, attn_mask=attention_mask, dropout_p=dropout,
        scale=scaling, is_causal=is_causal)
    return result.transpose(1, 2).contiguous(), None


class ModelTokenCounter:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.name = 'model-tokenizer:' + tokenizer.name_or_path

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def count_many(self, texts):
        if not texts:
            return []
        return [len(ids) for ids in self.tokenizer(texts, add_special_tokens=False,
                                                 padding=False, truncation=False)['input_ids']]


@dataclass
class Generation:
    output: str
    ttft_ms: float
    elapsed_ms: float
    input_tokens: int
    output_tokens: int


class LocalModel:
    def __init__(self, path, device='auto', threads=4, attention='auto', prompt_policy='concise-v3',prefill_chunk=0,quantization='none'):
        from .prepare_model import verify_snapshot
        self.manifest=verify_snapshot(path)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, AttentionInterface
        torch.set_num_threads(threads)
        self.torch = torch
        self.device = ('cuda' if torch.cuda.is_available() else 'cpu') if device == 'auto' else device
        self.device_type = torch.device(self.device).type
        if quantization not in {'none','nf4'}: raise ValueError('unsupported quantization mode')
        if quantization!='none' and self.device_type!='cuda': raise ValueError('this optional NF4 evaluation backend requires CUDA')
        self.quantization=quantization
        self.prompt_policy = prompt_policy
        if prefill_chunk<0: raise ValueError('prefill chunk must be nonnegative')
        self.prefill_chunk = prefill_chunk
        self.attention = 'sdpa'
        if attention == 'expanded' or (attention == 'auto' and self.device_type == 'cuda'
                                      and not torch.backends.cuda.is_flash_attention_available()):
            from transformers.masking_utils import AttentionMaskInterface, ALL_MASK_ATTENTION_FUNCTIONS
            AttentionInterface.register('context-expanded-sdpa', expanded_kv_sdpa)
            AttentionMaskInterface.register('context-expanded-sdpa', ALL_MASK_ATTENTION_FUNCTIONS['sdpa'])
            self.attention = 'context-expanded-sdpa'
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        dtype = torch.float16 if self.device_type == 'cuda' else torch.float32
        load_options={}
        if quantization=='nf4':
            from transformers import BitsAndBytesConfig
            load_options={'quantization_config':BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
                          bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=dtype),
                          'device_map':{'':str(torch.device(self.device))},'low_cpu_mem_usage':True}
        self.model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True,
                     trust_remote_code=False, dtype=dtype, attn_implementation=self.attention,**load_options)
        if quantization=='none': self.model=self.model.to(self.device)
        self.model.eval()
        self.counter = ModelTokenCounter(self.tokenizer)

    def prompt(self, context, task):
        policy = getattr(self, 'prompt_policy', 'original-v1')
        system = CONCISE_SYSTEM if policy == 'concise-v3' else REQUIREMENTS_SYSTEM if policy == 'requirements-v2' else SYSTEM
        if policy in {'requirements-v2','concise-v3'}:
            clauses = re.split(r'(?<=[.!?。])\s+|\n+', task.strip())
            task = 'Every requirement below is mandatory:\n' + '\n'.join('- ' + x for x in clauses if x)
        return self.tokenizer.apply_chat_template([
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': context + '\n\nCURRENT TASK:\n' + task}],
            tokenize=False, add_generation_prompt=True)

    def critique_prompt(self, context, task, draft):
        return self.tokenizer.apply_chat_template([
            {'role':'system','content':'You are a Python code reviewer. The public task specifies required behavior; context is evidence. Analyze the draft without executing it. Do not use hidden tests or invent extra requirements. Return concise review notes, not corrected code. Trace every requirement against concrete paths: validation before early returns, all input entries, ordering and duplicates, mutation and aliases, existing exports, and required helper calls at the correct validation boundary. Explain concrete mistakes and corrections. If no issue is found, say so.'},
            {'role':'user','content':context+'\n\nPUBLIC TASK:\n'+task+'\n\nDRAFT:\n'+draft}],
            tokenize=False,add_generation_prompt=True)

    def review_prompt(self, context, task, draft, feedback=None, review_notes=None):
        # Only caller-visible requirements/context and the candidate are used.
        # No evaluator, hidden oracle, test outcomes, or expected answers enter.
        clauses=re.split(r'(?<=[.!?。])\s+|\n+',task.strip())
        review='\n'.join('- '+clause for clause in clauses if clause)
        hints=''
        if feedback:
            hints='\n\nSTATIC REVIEW HINTS (visible-source heuristics, not test results):\n'+'\n'.join('- '+item for item in feedback)
        if review_notes:
            hints+='\n\nMODEL-GENERATED REVIEW NOTES (may be wrong; verify against the public requirements):\n'+review_notes
        return self.tokenizer.apply_chat_template([
            {'role':'system','content':CONCISE_SYSTEM+' You are reviewing a draft. Trace each requirement against the code. Correct any missing validation, input mutation, return identity, ordering, dependency calls, and existing-export preservation. Return the corrected complete target file even if the draft is already correct.'},
            {'role':'user','content':context+'\n\nMANDATORY REQUIREMENTS:\n'+review+'\n\nDRAFT TO REVIEW:\n'+draft+hints+'\n\nCheck every requirement and return the complete corrected target file.'}],
            tokenize=False,add_generation_prompt=True)

    def sync(self):
        if self.device_type == 'cuda':
            self.torch.cuda.synchronize(self.device)

    def generate(self, prompt, max_new_tokens=256):
        owner = self
        class TokenClock:
            first = None
            prompt_seen = False
            def put(self, value):
                if not self.prompt_seen:
                    self.prompt_seen = True
                    return
                if self.first is None and value.numel():
                    owner.sync()
                    self.first = time.perf_counter_ns()
            def end(self):
                pass
        clock = TokenClock()
        self.sync()
        start = time.perf_counter_ns()
        encoded = self.tokenizer(prompt, return_tensors='pt').to(self.device)
        input_count = encoded.input_ids.shape[1]
        limit = self.model.config.max_position_embeddings
        if input_count + max_new_tokens > limit:
            raise ValueError(f'prompt exceeds model context: {input_count}+{max_new_tokens}>{limit}')
        with self.torch.inference_mode():
            generation_kwargs={}
            if self.prefill_chunk and input_count>self.prefill_chunk:
                from transformers import DynamicCache
                cache=DynamicCache(config=self.model.config)
                # Leave a final nonempty chunk for generate's first step, so
                # its callback measures the same first generated token. The
                # cache contains only earlier prompt tokens; none are dropped.
                for offset in range(0,input_count-self.prefill_chunk,self.prefill_chunk):
                    end=min(offset+self.prefill_chunk,input_count-self.prefill_chunk)
                    self.model(input_ids=encoded.input_ids[:,offset:end],
                               attention_mask=encoded.attention_mask[:,:end],
                               past_key_values=cache,use_cache=True,return_dict=True,logits_to_keep=1)
                generation_kwargs['past_key_values']=cache
            output = self.model.generate(**encoded, max_new_tokens=max_new_tokens, do_sample=False,
                                        streamer=clock, pad_token_id=self.tokenizer.eos_token_id,**generation_kwargs)
        self.sync()
        end = time.perf_counter_ns()
        if clock.first is None:
            raise ValueError('no generated token')
        ids = output[0, input_count:]
        return Generation(self.tokenizer.decode(ids, skip_special_tokens=True),
                          (clock.first-start)/1e6, (end-start)/1e6, input_count, len(ids))
