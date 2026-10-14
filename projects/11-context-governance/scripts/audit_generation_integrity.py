"""Compare cached-prefill greedy IDs with an uncached prefill on real DEV prompts."""
import hashlib
import json
from pathlib import Path
import sys
import time
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from context_governance.bundles import load_case
from context_governance.core import govern, render
from context_governance.local_model import LocalModel
from context_governance.public_prompt import candidate_messages


def main():
    out = Path('G:/Hackathon-stage2-artifacts/project11/generation-integrity-20261013')
    out.mkdir(parents=True, exist_ok=False)
    report = {'completed': False, 'cases': [], 'scope': 'Greedy NF4 same-model prefill equivalence on two real DEV prompts; not arbitrary equivalence',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    began = time.perf_counter()
    model = LocalModel(str(ROOT / 'models/Qwen2.5-Coder-3B-Instruct'), device='cuda', quantization='nf4', prefill_chunk=1024)
    report['load_seconds'] = time.perf_counter()-began
    original = model.model.generate
    captured = []
    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        captured.append(result[0, kwargs['input_ids'].shape[1]:].tolist())
        return result
    model.model.generate = capture
    for case, mode in [('stable_topology', 'full'), ('merge_config', 'compressed')]:
        metadata, _, spec, items = load_case(ROOT / 'fixtures/combined-public-v17', case)
        context = render(items) if mode == 'full' else govern(spec, items, 650, model.counter, metadata['context_dependencies'])['context']
        prompt = model.tokenizer.apply_chat_template(candidate_messages(context, spec), tokenize=False, add_generation_prompt=True)
        (out / f'{case}-{mode}-prompt.txt').write_text(prompt, encoding='utf-8')
        rows=[]
        for chunk in [1024, 0]:
            model.prefill_chunk = chunk
            row=asdict(model.generate(prompt, 768))
            row.update(prefill_chunk=chunk, output_ids=captured[-1])
            rows.append(row)
        report['cases'].append({'id':case, 'mode':mode, 'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                                'equal_ids':rows[0]['output_ids']==rows[1]['output_ids'], 'runs':rows})
        (out/'partial.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'case':case, 'mode':mode, 'equal_ids':report['cases'][-1]['equal_ids'], 'tokens':[r['output_tokens'] for r in rows]}), flush=True)
    report.update(completed=True, wall_seconds=time.perf_counter()-began,
                  gpu_peak_allocated_bytes=model.torch.cuda.max_memory_allocated())
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__=='__main__': main()
