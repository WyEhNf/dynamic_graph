"""New fixed DEV model batch: same-model full/compressed, direct/public repair.

All hidden scoring occurs in a separate process after generation has ended.
"""
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from context_governance.bundles import load_case
from context_governance.core import govern, render
from context_governance.local_model import LocalModel, CONCISE_SYSTEM
from context_governance.candidate_gate import search_candidates, verify_public_contract
from context_governance.quality import check_code, extract_code
from context_governance.public_prompt import candidate_messages

DECLARATION = {'cases': ['stable_topology', 'merge_config'], 'modes': ['full', 'compressed'],
    'model': 'Qwen2.5-Coder-3B-Instruct', 'quantization': 'nf4', 'decoding': 'greedy',
    'max_new_tokens': 1536, 'candidate_budget': 2, 'context_budget': 650,
    'dataset': 'Adaptive DEV follow-up after public failures of v1; not independent holdout or official score',
    'initial_prompt': 'public requirements and context; no public tests',
    'repair_prompt': 'previous candidate plus trusted public tests and actual public failure',
    'quality_scope': 'All public passes remain finite checks, not proofs.'}
OUT = Path('G:/Hackathon-stage2-artifacts/project11/candidate-gate-public-prompt-v2-20261012')
SUITE = ROOT / 'fixtures/combined-public-v17'
CONTRACT = ROOT / 'adapters/correctness-v27'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'declaration.json').write_text(json.dumps(DECLARATION, indent=2), encoding='utf-8')
    # Preserve old Qwen3 partial; do not import its frozen runner or alter it.
    helper_spec = importlib.util.spec_from_file_location('frozen_public_protection', CONTRACT / 'protocol.py')
    helper = importlib.util.module_from_spec(helper_spec)
    sys.modules[helper_spec.name] = helper
    helper_spec.loader.exec_module(helper)
    for case in DECLARATION['cases']: verify_public_contract(CONTRACT, SUITE, case)
    import psutil
    import torch
    free_gpu, total_gpu = torch.cuda.mem_get_info()
    if free_gpu < 3 * 1024**3 or psutil.virtual_memory().available < 2 * 1024**3:
        raise RuntimeError('Insufficient free GPU/RAM for declared bounded batch')
    report = {'declaration': DECLARATION, 'script_sha256': sha(__file__),
        'candidate_gate_sha256': sha(ROOT / 'src/context_governance/candidate_gate.py'),
        'contract_manifest_sha256': sha(CONTRACT / 'contract-manifest.json'),
        'public_prompt_sha256': sha(ROOT / 'src/context_governance/public_prompt.py'),
        'cases': [], 'completed': False, 'gpu_free_before': free_gpu,
        'RAM_free_before': psutil.virtual_memory().available}
    started = perf_counter()
    model = LocalModel(str(ROOT / 'models' / DECLARATION['model']), device='cuda', quantization='nf4', prefill_chunk=1024)
    report['model_manifest'] = model.manifest
    report['load_seconds'] = perf_counter() - started
    report['warmup'] = asdict(model.generate(model.prompt('', 'Return only 1.'), 16))
    model.torch.cuda.reset_peak_memory_stats()
    def persist():
        (OUT / 'partial.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    persist()
    try:
        for case in DECLARATION['cases']:
            metadata, snapshot, spec, items = load_case(SUITE, case)
            test = verify_public_contract(CONTRACT, SUITE, case)
            compressed = govern(spec, items, 650, model.counter, metadata['context_dependencies'])
            protection = helper.check_compression(items, compressed, metadata['context_dependencies'])
            for mode in DECLARATION['modes']:
                context = render(items) if mode == 'full' else compressed['context']
                def prompt(previous, feedback):
                    return model.tokenizer.apply_chat_template(candidate_messages(context,spec,
                        previous=previous,public_tests=test.read_text(encoding='utf-8'),feedback=feedback or ''),
                        tokenize=False,add_generation_prompt=True)
                def generate(text, index):
                    with (OUT / f'{case}-{mode}-prompt{index}.txt').open('x',encoding='utf-8') as stream:stream.write(text)
                    generated = asdict(model.generate(text, DECLARATION['max_new_tokens']))
                    generated['final_output'] = generated['output']
                    if generated['output_tokens'] >= DECLARATION['max_new_tokens']:
                        generated['protocol_error'] = 'Declared token cap reached; conservatively reject potentially incomplete candidate'
                    # Save each raw generation before public execution or repair.
                    path = OUT / f'{case}-{mode}-candidate{index}.json'
                    with path.open('x', encoding='utf-8') as stream: json.dump(generated, stream, ensure_ascii=False, indent=2)
                    return generated
                def verify(answer):
                    result = check_code(answer, snapshot, metadata['target_file'], test)
                    if result['passed']:
                        errors = helper.check_exports(extract_code(answer), snapshot, metadata['target_file'], spec)
                        if errors: result.update(passed=False, reason='\n'.join(errors))
                    return result
                searched = search_candidates(generate, verify, prompt, budget=2)
                report['cases'].append({'id': case, 'mode': mode,
                    'snapshot_sha256': metadata['snapshot_sha256'], 'target_file': metadata['target_file'],
                    'public_test_sha256': sha(test), 'spec_sha256': sha(SUITE / 'spec' / f'{case}.md'),
                    'compression_protection': protection, 'search': asdict(searched)})
                persist()
                print(json.dumps({'case': case, 'mode': mode, 'status': searched.status, 'attempts': len(searched.attempts)}), flush=True)
        report.update(completed=True, wall_seconds=perf_counter() - started,
            gpu_peak_allocated_bytes=model.torch.cuda.max_memory_allocated(),
            gpu_peak_reserved_bytes=model.torch.cuda.max_memory_reserved(),
            generated_calls=sum(len(row['search']['attempts']) for row in report['cases']),
            hidden_evaluation_performed=False)
        persist()
        with (OUT / 'report.json').open('x', encoding='utf-8') as stream: json.dump(report, stream, ensure_ascii=False, indent=2)
    except BaseException as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        persist()
        raise
    finally:
        del model
        torch.cuda.empty_cache()


if __name__ == '__main__': main()
