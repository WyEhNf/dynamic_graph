"""Isolate one long-window cache-reservation candidate after the v20 capacity result."""
import hashlib
import json
from pathlib import Path
import time

root = Path(__file__).resolve().parents[1]
baseline = root / 'adapters/sdpa/research-v20/local_model.py'
folder = root / 'adapters/sdpa/research-v23'
folder.mkdir(parents=True, exist_ok=False)
original = baseline.read_text(encoding='utf-8')
needle = '                               past_key_values=cache,use_cache=True,return_dict=True,logits_to_keep=1)'
assert original.count(needle) == 1
changed = original.replace(needle, needle + '''
                    if input_count > getattr(self, 'kv_offload_min_tokens', 16384):
                        # Complete pending cache transfers before returning only
                        # unused allocator blocks. Live K/V tensors are retained.
                        self.sync()
                        self.torch.cuda.empty_cache()''')
(folder / 'local_model.py').write_text(changed, encoding='utf-8')
(folder / 'baseline-local-model.py').write_bytes(baseline.read_bytes())
record = {'prepared_unix': time.time(),
          'baseline_source_sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(),
          'candidate_source_sha256': hashlib.sha256((folder / 'local_model.py').read_bytes()).hexdigest(),
          'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'basis': 'v20 completed 32688 input tokens but peaked at 12211716096 reserved CUDA bytes; reservation or transfer pressure is a hypothesis, not a measured causal attribution.',
          'scope': 'Offloaded long-input prefill only: synchronize and release unused allocator blocks after each chunk. Same inputs, FP16 KV precision, weights and attention. Live tensors remain unchanged. Active model modules untouched.',
          'primary_source': 'https://docs.pytorch.org/docs/2.14/generated/torch.cuda.memory.empty_cache.html',
          'status': 'Not measured; no default promotion.'}
(folder / 'provenance.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record))
