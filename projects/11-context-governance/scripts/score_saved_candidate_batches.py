"""Offline held-back scoring AFTER both public-only generation runs have ended.

Scores do not choose candidates, change prompts or feed any generation call.
Rejected candidates are still rejected even when a diagnostic test passes.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from context_governance.bundles import load_case
from context_governance.quality import check_code

BASE=Path('G:/Hackathon-stage2-artifacts/project11')
NAMES=['candidate-gate-paired-20261012','candidate-gate-public-prompt-v2-20261012']


def main():
    batches=[]
    for name in NAMES:
        path=BASE/name/'report.json';report=json.loads(path.read_text())
        assert report['completed'] and not report['hidden_evaluation_performed']
        batches.append((name,path,report))
    result={'generation_ended_before_scoring':True,'selection_uses_hidden_feedback':False,
        'scope':'two previously used DEV cases, no independent generalization or correctness guarantee',
        'scorer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'batches':[]}
    for name,path,report in batches:
        rows=[]
        for r in report['cases']:
            metadata,snapshot,spec,items=load_case(ROOT/'fixtures/combined-public-v17',r['id'])
            test=ROOT/'fixtures/combined-public-v17/tests'/f"{r['id']}.py"
            attempts=[]
            for a in r['search']['attempts']:
                checked=check_code(a['generation']['final_output'],snapshot,metadata['target_file'],test)
                attempts.append({'index':a['index'],'public_passed':a['public_check']['passed'],
                    'held_back_check':checked,'input_tokens':a['generation']['input_tokens'],
                    'ttft_ms':a['generation']['ttft_ms'],'generation_ms':a['generation']['elapsed_ms']})
            assert r['search']['selected'] is None
            rows.append({'id':r['id'],'mode':r['mode'],'selected':None,'attempts':attempts,
                'held_back_test_sha256':hashlib.sha256(test.read_bytes()).hexdigest()})
        result['batches'].append({'name':name,'source_report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'public_selected':0,'records':rows})
    target=BASE/'candidate-gate-offline-scoring-20261012.json'
    with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'batches':len(result['batches']),'generation_calls':sum(len(r['attempts']) for b in result['batches'] for r in b['records']),
        'held_back_passed':sum(a['held_back_check']['passed'] for b in result['batches'] for r in b['records'] for a in r['attempts']),
        'public_selected':0,'output':str(target)}))


if __name__=='__main__':main()
