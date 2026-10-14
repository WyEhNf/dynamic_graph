"""Refine the unmeasured isolated candidate to preserve ordinary-window dispatch."""
import hashlib
import json
import time
from pathlib import Path

root=Path(__file__).resolve().parents[1]
folder=root/'adapters/sdpa/research-v19b'
folder.mkdir(parents=True,exist_ok=False)
baseline=(root/'src/context_governance/local_model.py').read_text(encoding='utf-8')
start=baseline.index('def expanded_kv_sdpa(')
end=baseline.index('\n\nclass ModelTokenCounter:',start)
old_function=baseline[start:end].replace('def expanded_kv_sdpa(','def baseline_expanded_kv_sdpa(',1)
candidate=(root/'adapters/sdpa/research-v19/local_model.py').read_text(encoding='utf-8')
point=candidate.index('    import torch\n',candidate.index('def expanded_kv_sdpa('))
candidate=candidate[:point]+'''    if key.shape[-2] <= getattr(module, '_context_head_group_min_tokens', 16384):
        return baseline_expanded_kv_sdpa(module, query, key, value, attention_mask,
                                       dropout=dropout, scaling=scaling, is_causal=is_causal, **kwargs)
'''+candidate[point:]
point=candidate.index('def expanded_kv_sdpa(')
candidate=candidate[:point]+old_function+'\n\n'+candidate[point:]
(folder/'local_model.py').write_text(candidate,encoding='utf-8')
(folder/'baseline-local-model.py').write_bytes((root/'src/context_governance/local_model.py').read_bytes())
record={'frozen_unix':time.time(),'threshold_key_tokens':16384,
        'scope':'Isolated candidate only. Original dispatch at <=16384 KV tokens; longer contexts serialize KV-head groups. No new quality results yet; active package unchanged.',
        'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.py')},
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(folder/'provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
