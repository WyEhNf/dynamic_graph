"""Offline public contract compatibility; must not be imported by generation."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
ADAPTER=ROOT/'adapters'/'correctness-v26'
SUITE=ROOT/'fixtures'/'combined-public-v17'
sys.path.insert(0,str(ROOT/'adapters'/'research-v24'))
from context_governance.bundles import load_case
from context_governance.quality import check_code

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    output=ROOT/'artifacts'/'public-contracts-all30-v26-offline-audit.json'
    if output.exists(): raise ValueError('refuse overwriting historical evidence')
    manifest_path=ADAPTER/'all30-contract-manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    original=json.loads((ROOT/'artifacts'/'public-contracts-v26-offline-audit.json').read_text(encoding='utf-8'))
    previous={case['id']:case for case in original['cases']}
    history_path=ROOT/'artifacts'/'research-model-v22-public-contract-nf4-7b.json'
    history=json.loads(history_path.read_text(encoding='utf-8'))
    outputs={c['id']:c['runs']['compressed'][0]['output'] for c in history['cases']}
    report={'origin':'Offline audit: references only validate independently authored public checks; outcomes never enter candidate prompts',
            'manifest_sha256':sha(manifest_path),'original10_audit_sha256':sha(ROOT/'artifacts'/'public-contracts-v26-offline-audit.json'),
            'source_report_sha256':sha(history_path),'cases':[]}
    start=time.perf_counter()
    for case_id,entry in manifest['cases'].items():
        test=ADAPTER/'public_contracts'/f'{case_id}.py'
        if sha(test)!=entry['test_sha256'] or sha(SUITE/'spec'/f'{case_id}.md')!=entry['spec_sha256']:
            raise ValueError('public contract/spec changed')
        if case_id in previous:
            report['cases'].append(dict(previous[case_id],reused_prior_audit=True)); continue
        metadata,snapshot,spec,items=load_case(SUITE,case_id)
        reference=check_code((SUITE/'oracle'/f'{case_id}.py').read_text(encoding='utf-8'),snapshot,metadata['target_file'],test)
        candidate=check_code(outputs[case_id],snapshot,metadata['target_file'],test)
        report['cases'].append({'id':case_id,'reference_public_check':reference,'v22_compressed_public_check':candidate})
        print(json.dumps({'id':case_id,'reference_pass':reference['passed'],'v22_pass':candidate['passed']}),flush=True)
    report['additional_elapsed_seconds']=time.perf_counter()-start
    report['reference_public_pass']=sum(c['reference_public_check']['passed'] for c in report['cases'])
    report['historic_v22_public_pass']=sum(c['v22_compressed_public_check']['passed'] for c in report['cases'])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'reference_pass':report['reference_public_pass'],'v22_public_pass':report['historic_v22_public_pass'],'cases':len(report['cases'])}),flush=True)
    if report['reference_public_pass']!=len(report['cases']): raise RuntimeError('Public checks need independent spec review; do not blindly tune checks to reference outputs')

if __name__=='__main__': main()
