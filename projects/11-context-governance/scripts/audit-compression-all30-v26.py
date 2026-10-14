"""CPU exact identified-closure/bytes audit, not arbitrary semantic equivalence."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'adapters'/'research-v24'))
sys.path.insert(0,str(ROOT/'adapters'/'correctness-v26'))
from context_governance.bundles import load_case
from context_governance.core import govern
from context_governance.local_model import ModelTokenCounter
from protocol import check_compression

def main():
    path=ROOT/'artifacts'/'compression-protection-all30-v26.json'
    if path.exists(): raise ValueError('refuse overwriting historical evidence')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(str(ROOT/'models'/'Qwen2.5-Coder-7B-Instruct'),trust_remote_code=False,local_files_only=True)
    counter=ModelTokenCounter(tokenizer)
    suite=ROOT/'fixtures'/'combined-public-v17'
    ids=json.loads((suite/'manifest.json').read_text(encoding='utf-8'))['case_ids']
    report={'origin':'CPU static identified closure, source order and exact protected/code bytes audit; no generation and no quality proof',
            'model_loaded':False,'tokenizer':'existing Qwen2.5-Coder-7B-Instruct only',
            'suite_manifest_sha256':hashlib.sha256((suite/'manifest.json').read_bytes()).hexdigest(),
            'frozen_v24_manifest_sha256':hashlib.sha256((ROOT/'adapters'/'research-v24'/'freeze-manifest.json').read_bytes()).hexdigest(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':[]}
    start=time.perf_counter()
    for case_id in ids:
        metadata,snapshot,spec,items=load_case(suite,case_id)
        governed=govern(spec,items,650,counter,metadata['context_dependencies'])
        evidence=check_compression(items,governed,metadata['context_dependencies'])
        report['cases'].append({'id':case_id,'protection':evidence,'metrics':governed['metrics']})
    report['elapsed_seconds']=time.perf_counter()-start
    torch=sys.modules.get('torch')
    report['gpu_initialized']=torch.cuda.is_initialized() if torch else False
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'audited':len(ids),'elapsed_seconds':report['elapsed_seconds'],'torch_imported':'torch' in sys.modules}))

if __name__=='__main__': main()
