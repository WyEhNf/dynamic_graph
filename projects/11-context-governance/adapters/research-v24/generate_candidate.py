"""Freeze the complete v22 baseline and build an isolated, opt-in KV policy candidate."""
import hashlib
import json
from pathlib import Path
import shutil
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'research-v22' / 'context_governance'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('baseline anchor changed: ' + old[:100])
    return text.replace(old, new, 1)

def main():
    paths = sorted(BASE.glob('*.py'))
    if len(paths) != 25:
        raise ValueError('expected complete 25-module v22 baseline')
    destination = HERE / 'context_governance'
    frozen = HERE / 'baseline-source'
    if destination.exists() or frozen.exists():
        raise FileExistsError('isolated candidate already generated')
    destination.mkdir(); frozen.mkdir()
    baseline = {p.name: sha(p) for p in paths}
    for path in paths:
        shutil.copyfile(path, destination/path.name)
        shutil.copyfile(path, frozen/path.name)
    path = destination / 'local_model.py'
    text = path.read_text(encoding='utf-8')
    text = replace_once(text, "prefill_chunk=0,quantization='none'):",
                        "prefill_chunk=0,quantization='none',kv_cache_policy='resident',kv_offload_min_tokens=16384):")
    text = replace_once(text, '        from .prepare_model import verify_snapshot\n',
        "        if kv_cache_policy not in {'resident','offloaded','reclaimed'}:\n"
        "            raise ValueError('unsupported KV cache policy')\n"
        "        if type(kv_offload_min_tokens) is not int or kv_offload_min_tokens < 0:\n"
        "            raise ValueError('KV offload threshold must be a nonnegative integer')\n"
        "        self.kv_cache_policy = kv_cache_policy\n"
        "        self.kv_offload_min_tokens = kv_offload_min_tokens\n"
        '        from .prepare_model import verify_snapshot\n')
    text = replace_once(text, '        self.device_type = torch.device(self.device).type\n',
        '        self.device_type = torch.device(self.device).type\n'
        "        if self.kv_cache_policy != 'resident' and self.device_type != 'cuda':\n"
        "            raise ValueError('nonresident KV cache policies require CUDA')\n")
    text = replace_once(text, '            generation_kwargs={}\n',
        '            generation_kwargs={}\n'
        "            cache_policy = getattr(self, 'kv_cache_policy', 'resident')\n"
        "            offload = (self.device_type == 'cuda' and cache_policy != 'resident'\n"
        "                       and input_count > getattr(self, 'kv_offload_min_tokens', 16384))\n")
    text = replace_once(text, '                cache=DynamicCache(config=self.model.config)\n',
                        '                cache=DynamicCache(config=self.model.config, offloading=offload)\n')
    text = replace_once(text, "                generation_kwargs['past_key_values']=cache\n",
        "                    if offload and cache_policy == 'reclaimed':\n"
        '                        # Finish pending transfers before releasing only unused\n'
        '                        # allocator blocks. Live K/V and input tokens remain.\n'
        '                        self.sync()\n'
        '                        self.torch.cuda.empty_cache()\n'
        "                generation_kwargs['past_key_values']=cache\n"
        '            if not generation_kwargs and offload:\n'
        "                generation_kwargs['cache_implementation']='offloaded'\n")
    path.write_text(text, encoding='utf-8')
    path = destination / 'run_local_eval.py'; text=path.read_text(encoding='utf-8')
    text = replace_once(text, "    parser.add_argument('--quantization',", 
        "    parser.add_argument('--kv-cache-policy',choices=['resident','offloaded','reclaimed'],default='resident',help='Opt-in CUDA KV cache placement and prefill allocator policy')\n"
        "    parser.add_argument('--kv-offload-min-tokens',type=int,default=16384,help='Offload only when input tokens strictly exceed this nonnegative threshold')\n"
        "    parser.add_argument('--quantization',")
    text = replace_once(text, '    args = parser.parse_args()\n',
        '    args = parser.parse_args()\n'
        "    if args.kv_offload_min_tokens < 0: parser.error('KV offload threshold must be nonnegative')\n")
    text = replace_once(text, 'quantization=args.quantization)\n',
        'quantization=args.quantization,kv_cache_policy=args.kv_cache_policy,kv_offload_min_tokens=args.kv_offload_min_tokens)\n')
    text = replace_once(text, "              'weight_quantization':model.quantization,\n",
        "              'weight_quantization':model.quantization,\n"
        "              'kv_cache_policy':model.kv_cache_policy,\n"
        "              'kv_offload_min_tokens':model.kv_offload_min_tokens,\n")
    path.write_text(text, encoding='utf-8')
    path = destination / 'public_examples.py'
    text = path.read_text(encoding='utf-8')
    text = replace_once(text, "    if not all(part.isidentifier() for part in module.split('.')):\n",
                        "    if not all(part.isidentifier() and not keyword.iskeyword(part) for part in module.split('.')):\n")
    path.write_text(text, encoding='utf-8')
    candidate={p.name:sha(p) for p in sorted(destination.glob('*.py'))}
    changed=[name for name in baseline if baseline[name]!=candidate[name]]
    assert changed == ['local_model.py','public_examples.py','run_local_eval.py']
    assert baseline == {p.name:sha(p) for p in BASE.glob('*.py')}
    record={'prepared_unix':time.time(),'baseline_source_sha256':baseline,'candidate_source_sha256':candidate,
            'generator_sha256':sha(Path(__file__)),
            'resource_reference_sha256':sha(HERE.parent/'sdpa'/'research-v23'/'local_model.py'),
            'changed_modules':changed,'scope':'Isolated v24 integration only. Default resident and v22 public protocols remain; v24 additionally rejects keyword module paths before template execution. Fake lifecycle tests are not a GPU speed, resource or model-quality measurement. Real v23 measurements are not v24 results.',
            'offload_predicate':'CUDA and policy != resident and input_tokens > kv_offload_min_tokens; default threshold 16384',
            'reclaim_scope':'reclaimed eligible chunked prefill only; sync then empty_cache after each explicit prefill call; no reclamation on decode/nonchunk path'}
    (HERE/'provenance.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'module_count':len(candidate),'changed_modules':changed,'provenance_sha256':sha(HERE/'provenance.json')}))

if __name__ == '__main__': main()
