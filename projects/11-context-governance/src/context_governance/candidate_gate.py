"""Bounded generation with trusted public feedback, never hidden-score feedback.

Opt-in API. A finite public pass is explicitly not a correctness proof.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .quality import check_code


@dataclass
class CandidateResult:
    attempts: list
    selected: int | None
    status: str


def verify_public_contract(root, suite, case_id):
    if not case_id or Path(case_id).name != case_id or '/' in case_id or '\\' in case_id:
        raise ValueError('case_id must be a single file stem')
    root, suite = Path(root), Path(suite)
    manifest = json.loads((root / 'contract-manifest.json').read_text(encoding='utf-8'))
    entry = manifest['cases'][case_id]
    test = root / 'public_contracts' / f'{case_id}.py'
    for path, key in ((test, 'test_sha256'), (suite / 'spec' / f'{case_id}.md', 'spec_sha256')):
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry[key]:
            raise ValueError('public contract/spec checksum mismatch')
    return test


def final_answer(raw, thinking=True):
    if thinking:
        if raw.count('</think>') != 1:
            raise ValueError('reasoning did not terminate exactly once')
        reasoning, raw = raw.split('</think>')
        if reasoning.count('<think>') > 1:
            raise ValueError('malformed reasoning delimiters')
    if '<think>' in raw or '</think>' in raw:
        raise ValueError('malformed reasoning delimiters')
    return raw.strip()


def search_candidates(generate, verify, make_prompt, budget=2):
    if type(budget) is not int or budget < 1:
        raise ValueError('candidate budget must be positive')
    attempts = []
    previous = feedback = None
    for index in range(budget):
        prompt = make_prompt(previous, feedback)
        started = perf_counter()
        generated = generate(prompt, index)
        generation_seconds = perf_counter() - started
        if not isinstance(generated, dict):
            raise ValueError('generator must return evidence dictionary')
        started = perf_counter()
        if generated.get('protocol_error'):
            checked = {'passed': False, 'reason': generated['protocol_error'], 'scope': 'public protocol'}
        elif not isinstance(generated.get('final_output'), str):
            checked = {'passed': False, 'reason': 'missing final output', 'scope': 'public protocol'}
        else:
            checked = verify(generated['final_output'])
        # A malformed checker response must never promote a candidate.
        if not isinstance(checked, dict) or type(checked.get('passed')) is not bool:
            raise ValueError('public verifier must return a boolean passed field')
        attempts.append({'index': index, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                         'generation': generated, 'public_check': checked,
                         'generation_seconds': generation_seconds,
                         'public_check_seconds': perf_counter() - started})
        if checked['passed']:
            return CandidateResult(attempts, index, 'PUBLIC_CHECKED_NOT_PROVED')
        previous = generated.get('final_output', '')
        feedback = str(checked.get('reason', 'public check failed'))
    return CandidateResult(attempts, None, 'NO_PUBLIC_CHECKED_CANDIDATE')


def search_public_code(generate, make_prompt, snapshot, target, public_test, *, budget=2):
    """Wire actual disposable-snapshot execution into the candidate loop.

The caller supplies only the public test path. check_code enforces the existing
pure-function fixture environment; it is not an arbitrary Python sandbox.
"""
    return search_candidates(generate,
        lambda output: check_code(output, Path(snapshot), target, Path(public_test)),
        make_prompt, budget)
