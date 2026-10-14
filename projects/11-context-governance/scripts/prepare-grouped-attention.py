"""Freeze an inference-only head-group SDPA candidate outside the active package."""
import hashlib
import json
import time
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=root/'src/context_governance/local_model.py'
destination=root/'adapters/sdpa/research-v19'
destination.mkdir(parents=True,exist_ok=False)
original=source.read_text(encoding='utf-8')
begin=original.index('def expanded_kv_sdpa(')
end=original.index('\n\nclass ModelTokenCounter:',begin)
function='''def expanded_kv_sdpa(module, query, key, value, attention_mask, dropout=0.0,
                     scaling=None, is_causal=None, **kwargs):
    """Evaluate independent KV-head groups with one group's expansion live."""
    import torch
    from transformers.integrations.sdpa_attention import repeat_kv
    if dropout != 0.0:
        raise ValueError('This isolated grouped SDPA candidate is inference-only')
    groups = query.shape[1] // key.shape[1]
    if query.shape[1] % key.shape[1]:
        raise ValueError('Query heads must be divisible by KV heads')
    if attention_mask is not None and attention_mask.ndim == 4:
        attention_mask = attention_mask[:, :, :, :key.shape[-2]]
        if attention_mask.shape[1] not in (1, query.shape[1]):
            raise ValueError('Unsupported attention-mask head dimension')
    if is_causal is None:
        is_causal = query.shape[2] > 1 and attention_mask is None and getattr(module, 'is_causal', True)
    result = torch.empty((*query.shape[:-1], value.shape[-1]), dtype=query.dtype, device=query.device)
    for head in range(key.shape[1]):
        first, last = head * groups, (head + 1) * groups
        mask = attention_mask
        if mask is not None and mask.ndim == 4 and mask.shape[1] != 1:
            mask = mask[:, first:last]
        expanded_key = repeat_kv(key[:, head:head+1], groups)
        expanded_value = repeat_kv(value[:, head:head+1], groups)
        group = torch.nn.functional.scaled_dot_product_attention(
            query[:, first:last], expanded_key, expanded_value, attn_mask=mask,
            dropout_p=0.0, scale=scaling, is_causal=is_causal)
        result[:, first:last] = group
        del group, expanded_key, expanded_value
    return result.transpose(1, 2).contiguous(), None
'''
changed=(original[:begin]+function+original[end:]).replace('context-expanded-sdpa','context-grouped-sdpa')
(destination/'local_model.py').write_text(changed,encoding='utf-8')
(destination/'baseline-local-model.py').write_bytes(source.read_bytes())
record={'frozen_unix':time.time(),'scope':'Isolated optional candidate. Attention heads are independent at inference; serialize KV-head groups to lower simultaneous expanded K/V allocation. Active model package and quality evaluation unchanged.',
        'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.glob('*.py')},
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(destination/'provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
