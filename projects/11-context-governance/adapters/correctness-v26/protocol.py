"""Generic public-contract candidate gate. No hidden test/oracle access."""
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_public_contract(root, suite, case_id):
    manifest = json.loads((root/'contract-manifest.json').read_text(encoding='utf-8'))
    entry = manifest['cases'][case_id]
    test = root/'public_contracts'/f'{case_id}.py'
    if sha(test) != entry['test_sha256'] or sha(suite/'spec'/f'{case_id}.md') != entry['spec_sha256']:
        raise ValueError('public contract/spec checksum mismatch')
    return test


def check_compression(items, result, dependencies):
    """Proves identified closure/byte preservation only, never arbitrary semantics."""
    original = {item.id:item for item in items}
    selected = {item['id']:item for item in result['selected']}
    if len(original) != len(items) or len(selected) != len(result['selected']):
        raise ValueError('duplicate context IDs')
    required = {item.id for item in items if item.protected}
    frontier = list(required)
    while frontier:
        for dep in dependencies.get(frontier.pop(), []):
            if dep not in original: raise ValueError('unresolved dependency')
            if dep not in required:
                required.add(dep)
                frontier.append(dep)
    if not required <= selected.keys(): raise ValueError('protected dependency closure was dropped')
    for name,item in selected.items():
        if name not in original: raise ValueError('invented context item')
        # Tool excerpts are allowed only for optional items, with explicit extraction.
        if original[name].kind == 'code' or name in required:
            if item['text'] != original[name].text or item['kind'] != original[name].kind:
                raise ValueError('code/required text was changed')
    order = [item.id for item in items if item.id in selected]
    if order != [item['id'] for item in result['selected']]: raise ValueError('context source order changed')
    return {'status':'IDENTIFIED_CLOSURE_AND_BYTES_PRESERVED', 'required':sorted(required),
            'selected_count':len(selected),
            'limitation':'Does not prove arbitrary runtime Python semantics or relevance of every discarded item.'}


def check_exports(candidate, snapshot, target, spec):
    """Existing public exports named unchanged in spec must retain their AST."""
    if 'Preserve the existing RELEASE_TAG constant and compatibility(value) function unchanged' not in spec:
        return []
    before = ast.parse((snapshot/target).read_text(encoding='utf-8'))
    after = ast.parse(candidate)
    def exports(tree):
        result = {}
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name == 'compatibility': result['compatibility']=ast.dump(node,include_attributes=False)
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'RELEASE_TAG' for t in node.targets): result['RELEASE_TAG']=ast.dump(node,include_attributes=False)
        return result
    original, actual = exports(before), exports(after)
    return [f'Public unchanged-export contract failed: {name}' for name,value in original.items() if actual.get(name)!=value]


def final_answer(raw, thinking=True):
    """Reject truncated reasoning; never pick a draft code block from reasoning."""
    if thinking:
        if '</think>' not in raw: raise ValueError('thinking did not terminate; no final answer')
        raw = raw.rsplit('</think>',1)[1]
    if '<think>' in raw or '</think>' in raw: raise ValueError('malformed reasoning delimiters')
    return raw.strip()


@dataclass
class CandidateResult:
    attempts: list
    selected: int | None
    status: str


def search_candidates(generate, verify, make_prompt, budget=2):
    """Bounded sequential candidates; only public verifier feedback is visible.

    generate(prompt, index) returns a dictionary containing final_output.
    verify(output) returns public check evidence. No fallback gets a free pass.
    """
    if type(budget) is not int or budget < 1: raise ValueError('candidate budget must be positive')
    attempts = []
    previous = feedback = None
    for index in range(budget):
        prompt = make_prompt(previous, feedback)
        generated = generate(prompt,index)
        if generated.get('protocol_error'):
            checked = {'passed':False,'reason':generated['protocol_error'],'scope':'public protocol'}
        else:
            checked = verify(generated['final_output'])
        attempts.append({'index':index,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                         'generation':generated,'public_check':checked})
        if checked['passed']: return CandidateResult(attempts,index,'PUBLIC_CHECKED_NOT_PROVED')
        previous = generated.get('final_output','')
        feedback = str(checked.get('reason','public check failed'))
    return CandidateResult(attempts,None,'NO_PUBLIC_CHECKED_CANDIDATE')
