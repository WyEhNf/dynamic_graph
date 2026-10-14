"""Reproduce prompt hashes/token counts and replay all stored functional results."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace

from .bundles import load_case
from .core import govern, render
from .local_model import LocalModel, ModelTokenCounter
from .prepare_model import verify_snapshot
from .quality import check_code


def recorded_checker(report, source_snapshot=None):
    """Pin the historical guard, so later library policy cannot rewrite scores."""
    project=Path(__file__).resolve().parents[2]
    current=Path(__file__).parent/'quality.py'
    expected=report.get('source_sha256_at_start',{}).get('quality.py')
    candidates=([Path(source_snapshot)/'quality.py'] if source_snapshot else
                [current,*sorted(project.glob('research-v*-source/quality.py')),
                 *sorted((project/'adapters').glob('research-v*-source/quality.py'))])
    for candidate in candidates:
        if not candidate.is_file(): continue
        digest=hashlib.sha256(candidate.read_bytes()).hexdigest()
        if expected and digest!=expected: continue
        module_spec=importlib.util.spec_from_file_location('recorded_quality_guard',candidate)
        module=importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module.check_code,digest
    raise ValueError('Matching frozen quality guard missing; supply --source-snapshot')


def main():
    from transformers import AutoTokenizer
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',default='artifacts/local-model-evaluation.json')
    parser.add_argument('--suite',default='fixtures/selftest-v2')
    parser.add_argument('--source-snapshot',help='Optional matching frozen module directory for the historical quality guard')
    args=parser.parse_args()
    path=Path(args.report); report=json.loads(path.read_text(encoding='utf-8'))
    if 'summary' not in report: raise ValueError('evaluation did not complete')
    check_code,guard_sha=recorded_checker(report,args.source_snapshot)
    manifest=verify_snapshot(report['model'])
    if manifest['files']!=report['model_manifest']['files']: raise ValueError('model snapshot changed')
    tokenizer=AutoTokenizer.from_pretrained(report['model'],local_files_only=True,trust_remote_code=False)
    counter=ModelTokenCounter(tokenizer); owner=SimpleNamespace(tokenizer=tokenizer, prompt_policy=report.get('prompt_policy','original-v1'))
    suite=Path(args.suite); replay_count=0
    for case in report['cases']:
        metadata,root,spec,items=load_case(suite,case['id'])
        if metadata['snapshot_sha256']!=case['snapshot_sha256']: raise ValueError('engineering snapshot changed')
        test_file=suite/'tests'/f'{case["id"]}.py'
        if hashlib.sha256(test_file.read_bytes()).hexdigest()!=case['tests_sha256']: raise ValueError('functional tests changed')
        # Replay the exact recorded selection even after the policy evolves.
        # Snapshot and prompt hashes independently protect it from alterations.
        compressed={'context':case['governance']['context']}
        for mode,context in [('baseline',render(items)),('compressed',compressed['context'])]:
            prompt=LocalModel.prompt(owner,context,spec)
            if hashlib.sha256(prompt.encode()).hexdigest()!=case[mode+'_prompt_sha256']: raise ValueError('prompt reconstruction differs')
            tokens=len(tokenizer.encode(prompt,add_special_tokens=True))
            for run in case['runs'][mode]:
                expected_tokens=run['draft']['input_tokens'] if 'draft' in run else run['input_tokens']
                if tokens!=expected_tokens: raise ValueError('recorded model token count differs')
                if 'draft' in run:
                    critique=run.get('critique')
                    if critique:
                        critique_prompt=LocalModel.critique_prompt(owner,context,spec,run['draft']['output'])
                        if hashlib.sha256(critique_prompt.encode()).hexdigest()!=run['critique_prompt_sha256']:
                            raise ValueError('critique prompt reconstruction differs')
                        if len(tokenizer.encode(critique_prompt,add_special_tokens=True))!=critique['input_tokens']:
                            raise ValueError('critique token count differs')
                    examples=run.get('public_examples_generation')
                    public_result=None
                    if examples:
                        examples_prompt=LocalModel.examples_prompt(owner,context,spec,(root/metadata['target_file']).read_text(encoding='utf-8'),report.get('public_examples_protocol') or 'literal-v17')
                        if hashlib.sha256(examples_prompt.encode()).hexdigest()!=run['public_examples_prompt_sha256']:
                            raise ValueError('public examples prompt reconstruction differs')
                        if len(tokenizer.encode(examples_prompt,add_special_tokens=True))!=examples['input_tokens']:
                            raise ValueError('public examples token count differs')
                        from .public_examples import evaluate_examples
                        public_result=evaluate_examples(examples['output'],run['draft']['output'],root,metadata['target_file'],checker=check_code,public_task=spec if report.get('public_examples_protocol')=='public-contract-v21' else None)
                        if public_result!=run['public_examples_result']:
                            raise ValueError('public examples execution changed')
                    review_prompt=LocalModel.review_prompt(owner,context,spec,run['draft']['output'],run.get('review_feedback'),critique['output'] if critique else None,
                                                          public_result['feedback'] if public_result else None)
                    if hashlib.sha256(review_prompt.encode()).hexdigest()!=run['review_prompt_sha256']:
                        raise ValueError('review prompt reconstruction differs')
                    review_tokens=len(tokenizer.encode(review_prompt,add_special_tokens=True))
                    if review_tokens!=run['review']['input_tokens'] or tokens+review_tokens+(critique['input_tokens'] if critique else 0)+(examples['input_tokens'] if examples else 0)!=run['input_tokens']:
                        raise ValueError('cumulative draft/review token count differs')
                    draft_checked=check_code(run['draft']['output'],root,metadata['target_file'],test_file)
                    if draft_checked['passed']!=run['draft_functional']['passed']:
                        raise ValueError('draft functional outcome changed')
                    run['draft_functional']=draft_checked; replay_count+=1
                checked=check_code(run['output'],root,metadata['target_file'],test_file)
                if checked['passed']!=run['functional']['passed']: raise ValueError('recorded functional outcome changed')
                run['functional']=checked; replay_count+=1
        print(f'Reproduced {case["id"]}: prompt hashes, real tokens, functional results',flush=True)
    report['review']={'model_files_verified_at_finalization':True,'reproduced_prompt_hashes':2*len(report['cases']),
                      'review_prompt_hashes':sum('draft' in run for case in report['cases'] for runs in case['runs'].values() for run in runs),
                      'critique_prompt_hashes':sum('critique' in run for case in report['cases'] for runs in case['runs'].values() for run in runs),
                      'public_examples_prompt_hashes':sum('public_examples_generation' in run for case in report['cases'] for runs in case['runs'].values() for run in runs),
                      'functional_results_replayed':replay_count,'reviewed_unix':time.time()}
    report['review']['quality_guard_sha256']=guard_sha
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['review']),flush=True)


if __name__=='__main__': main()
