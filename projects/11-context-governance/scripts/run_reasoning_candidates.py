"""Predeclared full/compressed candidate optimization; public feedback only.

All raw prompts, token IDs, checks and source hashes are retained. Hidden scoring
is a separate post-generation process and cannot influence this run.
"""
import argparse
from dataclasses import asdict
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from context_governance.bundles import load_case
from context_governance.core import govern, render
from context_governance.local_model import LocalModel
from context_governance.candidate_gate import search_candidates, verify_public_contract
from context_governance.public_prompt import candidate_messages
from context_governance.quality import check_code, extract_code


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--model', default='Qwen3-8B')
    parser.add_argument('--suite', default='fixtures/combined-public-v17')
    parser.add_argument('--cases', nargs='+', default=['stable_topology','merge_config'])
    parser.add_argument('--modes', nargs='+', choices=['full','compressed'], default=['compressed'])
    parser.add_argument('--thinking', action='store_true')
    parser.add_argument('--reasoning-budget', type=int, default=0, help='Explicit bounded reasoning followed by final-answer completion; requires --thinking')
    parser.add_argument('--single-pass-budget', action='store_true', help='Apply reasoning boundary inside one decoding pass; preserves KV cache')
    parser.add_argument('--brief-analysis', action='store_true', help='Request a concise algorithm/invariant analysis before code')
    parser.add_argument('--max-new-tokens', type=int, default=3072)
    parser.add_argument('--candidate-budget', type=int, default=2)
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--seed', type=int, default=261013)
    parser.add_argument('--max-call-seconds', type=float, default=240)
    parser.add_argument('--deadline', default='2026-10-13T13:52:00+08:00')
    parser.add_argument('--prefill-chunk', type=int, default=256)
    args=parser.parse_args()
    if args.reasoning_budget<0 or (args.reasoning_budget and not args.thinking):
        parser.error('positive reasoning budget requires --thinking')
    if args.single_pass_budget and not args.reasoning_budget:
        parser.error('single-pass budget requires a positive reasoning budget')
    out=Path(args.out); out.mkdir(parents=True,exist_ok=False)
    suite=ROOT/args.suite
    deadline=datetime.fromisoformat(args.deadline).timestamp()
    sampling=({'temperature':.6 if args.thinking else .7,
               'top_p':.95 if args.thinking else .8,'top_k':20} if args.sample else None)
    declaration=vars(args)|{'sampling':sampling,'context_budget':650,
        'initial_prompt':'Public requirements/context only; no tests',
        'repair_prompt':'Actual public feedback/tests and previous final answer',
        'quality_scope':'Finite tests, not proof. DEV status is per suite provenance.',
        'shared_cpu':'Concurrent other project work; wall times are observations under contention.'}
    (out/'declaration.json').write_text(json.dumps(declaration,ensure_ascii=False,indent=2),encoding='utf-8')
    contract=ROOT/'adapters/correctness-v27'
    helper_spec=importlib.util.spec_from_file_location('frozen_export_protection',contract/'protocol.py')
    helper=importlib.util.module_from_spec(helper_spec); sys.modules[helper_spec.name]=helper; helper_spec.loader.exec_module(helper)
    tests={}
    for case in args.cases:
        if suite.name=='combined-public-v17': tests[case]=verify_public_contract(contract,suite,case)
        else:
            manifest=json.loads((suite/'manifest.json').read_text(encoding='utf-8'))
            tests[case]=suite/'public_contracts'/f'{case}.py'
            for name in (f'public_contracts/{case}.py',f'spec/{case}.md',f'metadata/{case}.json'):
                if sha(suite/name)!=manifest['files_sha256'][name]: raise ValueError('public preparation checksum mismatch')
    source_paths=[Path(__file__),contract/'protocol.py',*sorted((ROOT/'src/context_governance').glob('*.py'))]
    for source in source_paths:
        destination=out/'source'/source.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    report={'declaration':declaration,'completed':False,'cases':[],
            'started_unix':time.time(),'hidden_evaluation_performed':False,
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths}}
    def persist(): (out/'partial.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    persist(); began=time.perf_counter(); model=None
    try:
        if time.time()>=deadline: raise TimeoutError('declared experiment deadline passed before load')
        model=LocalModel(str(ROOT/'models'/args.model),device='cuda',quantization='nf4',prefill_chunk=args.prefill_chunk)
        model.torch.cuda.empty_cache()
        report.update(load_seconds=time.perf_counter()-began,model_manifest=model.manifest,
                      gpu_after_load_allocated=model.torch.cuda.memory_allocated())
        persist(); print(json.dumps({'loaded':args.model,'allocated':report['gpu_after_load_allocated']}),flush=True)
        for case in args.cases:
            metadata,snapshot,spec,items=load_case(suite,case)
            compressed=govern(spec,items,650,model.counter,metadata['context_dependencies'])
            protection=helper.check_compression(items,compressed,metadata['context_dependencies'])
            for mode in args.modes:
                workflow_start=time.perf_counter()
                request_started=time.perf_counter()
                if mode=='full':
                    context=render(items)
                    request_governance_ms=0.0
                else:
                    live=govern(spec,items,650,model.counter,metadata['context_dependencies'],measure_input=False)
                    if live['context']!=compressed['context']: raise ValueError('live governance selection changed')
                    context=live['context']
                    request_governance_ms=live['metrics']['governance_ms']
                request_overhead_ms=(time.perf_counter()-request_started)*1000
                def make_prompt(previous,feedback):
                    messages=candidate_messages(context,spec,previous=previous,
                        public_tests=tests[case].read_text(encoding='utf-8'),feedback=feedback or '')
                    if args.brief_analysis:
                        messages[0]['content']+=' Before writing code, briefly identify the algorithm and essential invariants. Avoid repeatedly paraphrasing requirements. Then implement the complete target file.'
                    return model.tokenizer.apply_chat_template(messages,tokenize=False,
                        add_generation_prompt=True,enable_thinking=args.thinking)
                def generate(prompt,index):
                    remaining=deadline-time.time()
                    if remaining<10: raise TimeoutError('declared experiment deadline reached')
                    stem=f'{case}-{mode}-candidate{index}'
                    (out/(stem+'-prompt.txt')).write_text(prompt,encoding='utf-8')
                    if args.reasoning_budget and args.single_pass_budget:
                        generated=model.generate_evidence(prompt,args.max_new_tokens,thinking=True,
                            sampling=sampling,seed=args.seed+index,max_seconds=min(args.max_call_seconds,remaining-5),
                            reasoning_budget=args.reasoning_budget)
                    elif args.reasoning_budget:
                        from context_governance.bounded_reasoning import generate_bounded_reasoning
                        generated=generate_bounded_reasoning(model.generate_evidence,model.tokenizer,prompt,
                            reasoning_budget=args.reasoning_budget,answer_budget=args.max_new_tokens,
                            sampling=sampling,seed=args.seed+index,max_seconds=min(args.max_call_seconds,remaining-5))
                    else:
                        generated=model.generate_evidence(prompt,args.max_new_tokens,thinking=args.thinking,
                            sampling=sampling,seed=args.seed+index,max_seconds=min(args.max_call_seconds,remaining-5))
                    (out/(stem+'.json')).write_text(json.dumps(generated,ensure_ascii=False,indent=2),encoding='utf-8')
                    print(json.dumps({'generated':stem,'tokens':generated['output_tokens'],'eos':generated['stopped_on_eos'],'seconds':generated['elapsed_ms']/1000}),flush=True)
                    return generated
                def verify(answer):
                    result=check_code(answer,snapshot,metadata['target_file'],tests[case])
                    if result['passed']:
                        errors=helper.check_exports(extract_code(answer),snapshot,metadata['target_file'],spec)
                        if errors: result.update(passed=False,reason='\n'.join(errors))
                    return result
                searched=search_candidates(generate,verify,make_prompt,budget=args.candidate_budget)
                report['cases'].append({'id':case,'mode':mode,'snapshot_sha256':metadata['snapshot_sha256'],
                    'target_file':metadata['target_file'],'spec_sha256':sha(suite/'spec'/f'{case}.md'),
                    'public_test_sha256':sha(tests[case]),'compression_protection':protection,
                    'governance':compressed['metrics'],'request_governance_ms':request_governance_ms,
                    'request_context_overhead_ms':request_overhead_ms,
                    'workflow_seconds':time.perf_counter()-workflow_start,
                    'search':asdict(searched)})
                persist(); print(json.dumps({'case':case,'mode':mode,'status':searched.status,'attempts':len(searched.attempts)}),flush=True)
        report['completed']=True
    except BaseException as error:
        report['failure']={'type':type(error).__name__,'message':str(error)}
        raise
    finally:
        report['wall_seconds']=time.perf_counter()-began
        if model is not None:
            report.update(gpu_peak_allocated_bytes=model.torch.cuda.max_memory_allocated(),
                          gpu_peak_reserved_bytes=model.torch.cuda.max_memory_reserved())
        persist()
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__': main()
