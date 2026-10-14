"""Reproduce prompt hashes/token counts and replay all stored functional results."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace

from .bundles import load_case
from .core import govern, render
from .local_model import LocalModel, ModelTokenCounter
from .prepare_model import verify_snapshot
from .quality import check_code


def main():
    from transformers import AutoTokenizer
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',default='artifacts/local-model-evaluation.json')
    parser.add_argument('--suite',default='fixtures/selftest-v2')
    args=parser.parse_args()
    path=Path(args.report); report=json.loads(path.read_text(encoding='utf-8'))
    if 'summary' not in report: raise ValueError('evaluation did not complete')
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
                    review_prompt=LocalModel.review_prompt(owner,context,spec,run['draft']['output'],run.get('review_feedback'),critique['output'] if critique else None)
                    if hashlib.sha256(review_prompt.encode()).hexdigest()!=run['review_prompt_sha256']:
                        raise ValueError('review prompt reconstruction differs')
                    review_tokens=len(tokenizer.encode(review_prompt,add_special_tokens=True))
                    if review_tokens!=run['review']['input_tokens'] or tokens+review_tokens+(critique['input_tokens'] if critique else 0)!=run['input_tokens']:
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
                      'functional_results_replayed':replay_count,'reviewed_unix':time.time()}
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['review']),flush=True)


if __name__=='__main__': main()
