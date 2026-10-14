"""Prepare adaptive public-feedback DEV follow-up; retain the first failed run."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'scripts/run_candidate_gate_paired.py').read_text(encoding='utf-8')
source=source.replace('from context_governance.quality import check_code, extract_code',
    'from context_governance.quality import check_code, extract_code\nfrom context_governance.public_prompt import candidate_messages')
source=source.replace('candidate-gate-paired-20261012','candidate-gate-public-prompt-v2-20261012')
source=source.replace('Previously used DEV; integration batch, not holdout or official score',
    'Adaptive DEV follow-up after public failures of v1; not independent holdout or official score')
start=source.index('                    user = context +')
end=source.index('\n                def generate',start)
source=source[:start]+'''                    return model.tokenizer.apply_chat_template(candidate_messages(context,spec,
                        previous=previous,public_tests=test.read_text(encoding='utf-8'),feedback=feedback or ''),
                        tokenize=False,add_generation_prompt=True)'''+source[end:]
needle='                    generated = asdict(model.generate(text, DECLARATION[\'max_new_tokens\']))'
source=source.replace(needle,'''                    with (OUT / f'{case}-{mode}-prompt{index}.txt').open('x',encoding='utf-8') as stream:stream.write(text)
'''+needle)
source=source.replace("'contract_manifest_sha256': sha(CONTRACT / 'contract-manifest.json'),",
    "'contract_manifest_sha256': sha(CONTRACT / 'contract-manifest.json'),\n        'public_prompt_sha256': sha(ROOT / 'src/context_governance/public_prompt.py'),")
with (ROOT/'scripts/run_candidate_gate_public_prompt_v2.py').open('x',encoding='utf-8') as stream:stream.write(source)
print('Prepared public-only v2 paired runner, unchanged model and candidate budget')
