"""Predeclared short DEV capability/resource smoke; never loads hidden tests."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from dataclasses import asdict

ROOT=Path(__file__).resolve().parents[1]
ADAPTER=ROOT/'adapters'/'correctness-v26'
SUITE=ROOT/'fixtures'/'combined-public-v17'
sys.path.insert(0,str(ROOT/'adapters'/'research-v24'))
sys.path.insert(0,str(ADAPTER))
from context_governance.bundles import load_case
from context_governance.core import govern
from context_governance.local_model import LocalModel, CONCISE_SYSTEM
from context_governance.quality import check_code, extract_code
from protocol import sha, verify_public_contract, check_compression, check_exports, search_candidates


DECLARATION={
    'version':'qwen3-smoke-v26','cases':['stable_topology','merge_config'],
    'dataset_status':'Existing DEV tasks; capability/resource smoke only; not holdout or official score',
    'mode':'compressed','context_budget':650,'max_candidates_per_case':2,
    'seeds_per_candidate':[260110,260111],'max_new_tokens':4096,
    'sampling':{'temperature':0.6,'top_p':0.95,'top_k':20,'do_sample':True},
    'thinking':True,'quantization':'nf4','prefill_chunk':1024,
    'attention':'auto','kv_cache_policy':'resident','warmup_calls':1,
    'public_test_feedback':True,
    'selection':'First candidate passing fixed public checks; no hidden tests/reference code are read by this process',
    'timing':'First generated token is reasoning-token TTFT; all reasoning/repair generation time and tokens counted',
}


def main():
    declaration=ADAPTER/'qwen3-smoke-declaration.json'
    if not declaration.exists() or json.loads(declaration.read_text(encoding='utf-8')) != DECLARATION:
        raise ValueError('smoke declaration missing or changed')
    output_path=ROOT/'artifacts'/'qwen3-smoke-v26.json'
    partial_path=output_path.with_suffix('.partial.json')
    if output_path.exists() or partial_path.exists(): raise ValueError('refuse overwriting existing smoke evidence')
    # Validate all public contracts before allocating GPU/model resources.
    for case_id in DECLARATION['cases']: verify_public_contract(ADAPTER,SUITE,case_id)
    contract_manifest=json.loads((ADAPTER/'contract-manifest.json').read_text(encoding='utf-8'))
    if sha(ADAPTER/'protocol.py')!=contract_manifest['protocol_sha256']:
        raise ValueError('frozen candidate protocol changed')
    frozen_root=ROOT/'adapters'/'research-v24'
    frozen_manifest=json.loads((frozen_root/'freeze-manifest.json').read_text(encoding='utf-8'))
    for name,digest in frozen_manifest['file_sha256'].items():
        if sha(frozen_root/name)!=digest: raise ValueError(f'frozen v24 source changed: {name}')
    import psutil
    process=psutil.Process()
    report={'declaration':DECLARATION,'declaration_sha256':sha(declaration),
            'script_sha256':sha(Path(__file__)),'protocol_sha256':sha(ADAPTER/'protocol.py'),
            'public_contract_manifest_sha256':sha(ADAPTER/'contract-manifest.json'),
            'frozen_v24_manifest_sha256':sha(ROOT/'adapters'/'research-v24'/'freeze-manifest.json'),
            'python':platform.python_version(),'cases':[],'started_unix':time.time()}
    began=time.perf_counter()
    model=LocalModel(str(ROOT/'models'/'Qwen3-8B'),device='cuda',attention='auto',
                     prompt_policy='concise-v3',prefill_chunk=1024,quantization='nf4')
    torch=model.torch
    report['load_seconds']=time.perf_counter()-began
    report['model_manifest']=model.manifest
    report['model_config_max_position_embeddings']=model.model.config.max_position_embeddings
    report['model_card_native_context_tokens']=32768
    report['torch']=torch.__version__
    report['gpu_name']=torch.cuda.get_device_name()
    report['gpu_total_bytes']=torch.cuda.get_device_properties(0).total_memory
    report['load_gpu_allocated_bytes']=torch.cuda.memory_allocated()
    report['load_gpu_reserved_bytes']=torch.cuda.memory_reserved()
    report['load_cpu_rss_bytes']=process.memory_info().rss
    report['completed']=False
    partial_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checkpoint':'model_loaded','load_seconds':report['load_seconds'],
                     'gpu_allocated_bytes':report['load_gpu_allocated_bytes'],
                     'gpu_reserved_bytes':report['load_gpu_reserved_bytes'],
                     'cpu_rss_bytes':report['load_cpu_rss_bytes']}),flush=True)
    rss_samples=[report['load_cpu_rss_bytes']]
    think_end=model.tokenizer.convert_tokens_to_ids('</think>')
    eos=model.model.generation_config.eos_token_id
    eos_set=set(eos if isinstance(eos,list) else [eos])

    def generate(prompt,index,max_tokens=4096):
        seed=DECLARATION['seeds_per_candidate'][index]
        torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        class Clock:
            first=None
            prompt_seen=False
            def put(self,value):
                if not self.prompt_seen: self.prompt_seen=True; return
                if self.first is None and value.numel():
                    model.sync(); self.first=time.perf_counter_ns()
            def end(self): pass
        clock=Clock()
        model.sync(); start=time.perf_counter_ns()
        encoded=model.tokenizer(prompt,return_tensors='pt').to(model.device)
        count=encoded.input_ids.shape[1]
        if count+max_tokens>model.model.config.max_position_embeddings: raise ValueError('model context limit exceeded')
        with torch.inference_mode():
            generation_kwargs={}
            if model.prefill_chunk and count>model.prefill_chunk:
                from transformers import DynamicCache
                cache=DynamicCache(config=model.model.config)
                for offset in range(0,count-model.prefill_chunk,model.prefill_chunk):
                    end=min(offset+model.prefill_chunk,count-model.prefill_chunk)
                    model.model(input_ids=encoded.input_ids[:,offset:end],
                        attention_mask=encoded.attention_mask[:,:end],past_key_values=cache,
                        use_cache=True,return_dict=True,logits_to_keep=1)
                generation_kwargs['past_key_values']=cache
            generated=model.model.generate(**encoded,max_new_tokens=max_tokens,
                        do_sample=True,temperature=0.6,top_p=0.95,top_k=20,
                        streamer=clock,pad_token_id=model.tokenizer.eos_token_id,**generation_kwargs)
        model.sync(); end=time.perf_counter_ns()
        ids=generated[0,count:].tolist()
        raw=model.tokenizer.decode(ids,skip_special_tokens=False)
        result={'seed':seed,'raw_output':raw,'input_tokens':count,'output_tokens':len(ids),
                'elapsed_ms':(end-start)/1e6,'first_generated_token_ttft_ms':(clock.first-start)/1e6 if clock.first else None,
                'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),
                'gpu_peak_reserved_bytes':torch.cuda.max_memory_reserved()}
        rss_samples.append(process.memory_info().rss)
        positions=[i for i,token in enumerate(ids) if token == think_end]
        if not positions:
            result.update(final_output='',protocol_error='thinking did not terminate; no final answer',reasoning_tokens=len(ids),final_answer_tokens=0)
        else:
            boundary=positions[-1]+1
            result.update(final_output=model.tokenizer.decode(ids[boundary:],skip_special_tokens=True).strip(),
                          reasoning_tokens=boundary,final_answer_tokens=len(ids)-boundary)
            if not ids or ids[-1] not in eos_set:
                result['protocol_error']='generation hit token limit without EOS; incomplete answer refused'
        return result

    warm_prompt=model.tokenizer.apply_chat_template([{'role':'user','content':'Return only the number 1. /no_think'}],tokenize=False,add_generation_prompt=True,enable_thinking=True)
    report['warmup']=generate(warm_prompt,0,32)
    torch.cuda.reset_peak_memory_stats()
    for case_id in DECLARATION['cases']:
        metadata,snapshot,spec,items=load_case(SUITE,case_id)
        public_test=verify_public_contract(ADAPTER,SUITE,case_id)
        governed=govern(spec,items,650,model.counter,metadata['context_dependencies'])
        protection=check_compression(items,governed,metadata['context_dependencies'])
        test_source=public_test.read_text(encoding='utf-8')
        def make_prompt(previous,feedback):
            instructions=CONCISE_SYSTEM+' This environment allows pure functions only: do not write object attributes or use process/file introspection. Think through every public requirement and test, choose a simple robust algorithm, then return exactly one complete Python file.'
            user=governed['context']+'\n\nMANDATORY PUBLIC REQUIREMENTS:\n'+spec+'\n\nTRUSTED PUBLIC CHECKS (finite checks, not the complete specification):\n'+test_source
            if previous is not None:
                user+='\n\nPREVIOUS FINAL CANDIDATE:\n'+previous+'\n\nPUBLIC EXECUTION FEEDBACK:\n'+feedback+'\nCorrect the cause while preserving all other requirements. Return the full file.'
            return model.tokenizer.apply_chat_template([{'role':'system','content':instructions},{'role':'user','content':user}],tokenize=False,add_generation_prompt=True,enable_thinking=True)
        def verify(answer):
            start=time.perf_counter()
            result=check_code(answer,snapshot,metadata['target_file'],public_test)
            if result['passed']:
                errors=check_exports(extract_code(answer),snapshot,metadata['target_file'],spec)
                if errors: result.update(passed=False,reason='\n'.join(errors))
            result['scope']='finite reviewed public DEV contract; not full-domain proof'
            result['elapsed_seconds']=time.perf_counter()-start
            return result
        start=time.perf_counter()
        searched=search_candidates(generate,verify,make_prompt,budget=2)
        report['cases'].append({'id':case_id,'snapshot_sha256':metadata['snapshot_sha256'],
                               'spec_sha256':sha(SUITE/'spec'/f'{case_id}.md'),'public_test_sha256':sha(public_test),
                               'compression_protection':protection,'governance':governed['metrics'],
                               'search':asdict(searched),'workflow_seconds':time.perf_counter()-start})
        partial_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'case':case_id,'status':searched.status,'attempts':len(searched.attempts)}),flush=True)
    report['wall_seconds']=time.perf_counter()-began
    report['gpu_peak_allocated_bytes']=torch.cuda.max_memory_allocated()
    report['gpu_peak_reserved_bytes']=torch.cuda.max_memory_reserved()
    report['cpu_rss_sampled_max_bytes']=max(rss_samples)
    report['cpu_rss_sampling_limitation']='Sampled after loading and each generation; not a continuous peak.'
    report['timed_generation_calls']=sum(len(c['search']['attempts']) for c in report['cases'])
    report['total_generation_calls']=report['timed_generation_calls']+1
    report['timed_output_tokens_including_reasoning']=sum(a['generation']['output_tokens'] for c in report['cases'] for a in c['search']['attempts'])
    report['hidden_evaluation']='Not performed in this smoke process. Public pass cannot establish hidden/full-domain success.'
    report['completed']=True
    output_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    partial_path.unlink()
    print(json.dumps({'output':str(output_path),'wall_seconds':report['wall_seconds'],'gpu_peak_allocated_bytes':report['gpu_peak_allocated_bytes']}),flush=True)
    del model
    torch.cuda.empty_cache()

if __name__ == '__main__': main()
