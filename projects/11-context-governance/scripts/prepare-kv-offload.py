"""Freeze an optional long-window CPU KV-cache candidate using the installed API."""
import hashlib
import json
import time
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=root/'src/context_governance/local_model.py'
folder=root/'adapters/sdpa/research-v20'
folder.mkdir(parents=True,exist_ok=False)
original=source.read_text(encoding='utf-8')
needle='cache=DynamicCache(config=self.model.config)'
assert original.count(needle)==1
changed=original.replace(needle,"cache=DynamicCache(config=self.model.config, offloading=input_count > getattr(self, 'kv_offload_min_tokens', 16384))")
needle="            output = self.model.generate(**encoded, max_new_tokens=max_new_tokens, do_sample=False,"
assert changed.count(needle)==1
changed=changed.replace(needle,"            if not generation_kwargs and input_count > getattr(self, 'kv_offload_min_tokens', 16384):\n                generation_kwargs['cache_implementation']='offloaded'\n"+needle)
(folder/'local_model.py').write_text(changed,encoding='utf-8')
(folder/'baseline-local-model.py').write_bytes(source.read_bytes())
record={'frozen_unix':time.time(),'default_threshold_input_tokens':16384,
        'scope':'Isolated optional long-input candidate. Use Transformers DynamicCache offloading, preserving cache tensor precision. Installed 4.57.6 API checked against official 4.57.1 cache docs. Active model package unchanged; no measurements yet.',
        'primary_source':'https://huggingface.co/docs/transformers/v4.57.1/kv_cache',
        'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.py')},
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(folder/'provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
