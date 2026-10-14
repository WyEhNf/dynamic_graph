"""Freeze independently spec-derived DEV checks; optional offline reference audit.

Only this preparation script may access reference code. The candidate protocol
never imports this script or receives reference/hidden evaluation outcomes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT/'adapters'/'correctness-v26'
SUITE = ROOT/'fixtures'/'combined-public-v17'
sys.path.insert(0,str(ROOT/'adapters'/'research-v24'))
from context_governance.bundles import load_case
from context_governance.quality import check_code

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit-reference',action='store_true')
    args=parser.parse_args()
    cases={p.stem:{'spec_sha256':sha(SUITE/'spec'/f'{p.stem}.md'),'test_sha256':sha(p)}
           for p in sorted((ADAPTER/'public_contracts').glob('*.py'))}
    data={'version':'public-contracts-v26','origin':'Manually derived from public natural-language DEV requirements; not official; development-informed; not holdout',
          'scope':'Finite public checks, not full-domain proofs. No hidden tests were copied.',
          'cases':cases,'suite_manifest_sha256':sha(SUITE/'manifest.json'),
          'script_sha256':sha(Path(__file__)),'protocol_sha256':sha(ADAPTER/'protocol.py')}
    path=ADAPTER/'contract-manifest.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != data: raise ValueError('frozen public contract changed; use a new version')
    else: path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.audit_reference:
        print(json.dumps({'frozen':len(cases),'manifest_sha256':sha(path)})); return
    started=time.perf_counter()
    historic=json.loads((ROOT/'artifacts'/'research-model-v22-public-contract-nf4-7b.json').read_text(encoding='utf-8'))
    outputs={c['id']:c['runs']['compressed'][0]['output'] for c in historic['cases']}
    evidence={'origin':'Offline contract compatibility audit only; reference outcomes must not enter candidate prompts/selection',
              'manifest_sha256':sha(path),'source_report_sha256':sha(ROOT/'artifacts'/'research-model-v22-public-contract-nf4-7b.json'), 'cases':[]}
    for case_id in cases:
        meta,snapshot,spec,items=load_case(SUITE,case_id)
        reference=check_code((SUITE/'oracle'/f'{case_id}.py').read_text(encoding='utf-8'),snapshot,meta['target_file'],ADAPTER/'public_contracts'/f'{case_id}.py')
        candidate=check_code(outputs[case_id],snapshot,meta['target_file'],ADAPTER/'public_contracts'/f'{case_id}.py')
        evidence['cases'].append({'id':case_id,'reference_public_check':reference,'v22_compressed_public_check':candidate})
        print(json.dumps({'id':case_id,'reference_pass':reference['passed'],'v22_pass':candidate['passed']}),flush=True)
    evidence['elapsed_seconds']=time.perf_counter()-started
    output=ROOT/'artifacts'/'public-contracts-v26-offline-audit.json'
    if output.exists(): raise ValueError('refuse overwriting historical evidence')
    output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    if not all(c['reference_public_check']['passed'] for c in evidence['cases']): raise RuntimeError('public check compatibility audit failed; inspect specification, not tune to references')

if __name__ == '__main__': main()
