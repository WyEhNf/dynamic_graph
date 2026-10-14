"""Execute bounded literal examples derived from public inputs, never hidden tests.

Model output supplies data only. The trusted unittest template supplies all code.
The existing pure-function guard and isolated process apply to the draft.
"""
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile

from .quality import check_code


def _literal(text):
    if not isinstance(text, str) or len(text) > 8192:
        raise ValueError('literal must be bounded text')
    try:
        text.encode('utf-8')
    except UnicodeError:
        raise ValueError('literal has invalid Unicode') from None
    tree = ast.parse(text, mode='eval')
    nodes = list(ast.walk(tree))
    if len(nodes) > 512:
        raise ValueError('literal has too many nodes')
    allowed = (ast.Expression, ast.Constant, ast.Tuple, ast.List, ast.Dict,
               ast.Set, ast.Load, ast.UnaryOp, ast.UAdd, ast.USub)
    if any(not isinstance(n, allowed) for n in nodes):
        raise ValueError('only literal data is allowed')
    def visit(node, depth=0):
        if depth > 16:
            raise ValueError('literal nesting too deep')
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str) and len(node.value) > 4096:
                raise ValueError('string too long')
            if isinstance(node.value, int) and node.value.bit_length() > 256:
                raise ValueError('integer too large')
            if isinstance(node.value, float) and not math.isfinite(node.value):
                raise ValueError('nonfinite float')
            if type(node.value) not in (type(None), bool, int, float, str):
                raise ValueError('unsupported literal type')
        for child in ast.iter_child_nodes(node):
            visit(child, depth + 1)
    visit(tree)
    return ast.literal_eval(tree)


def parse_examples(response, target_source):
    if len(response) > 32768:
        raise ValueError('example response too long')
    blocks = re.findall(r'```(?:json)?\s*\n(.*?)```', response, re.S | re.I)
    text = blocks[0] if blocks else response.strip()
    entries = json.loads(text)
    if not isinstance(entries, list) or not 1 <= len(entries) <= 6:
        raise ValueError('expected one to six examples')
    functions = {n.name for n in ast.parse(target_source).body
                 if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')}
    parsed = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) not in (
                {'function', 'args_python', 'expected_python'},
                {'function', 'args_python', 'raises'}):
            raise ValueError('invalid example fields')
        name = entry['function']
        if not isinstance(name, str) or name not in functions:
            raise ValueError('function must be present in the public target file')
        args = _literal(entry['args_python'])
        if not isinstance(args, tuple) or len(args) > 12:
            raise ValueError('args_python must be a tuple with at most twelve arguments')
        # Unparse the checked tree: comments/newlines cannot swallow generated
        # template punctuation, and set ordering does not depend on hash seeds.
        item = {'function': name, 'args': args, 'args_source': ast.unparse(ast.parse(entry['args_python'],mode='eval'))}
        if 'raises' in entry:
            if entry['raises'] not in ('ValueError', 'TypeError', 'KeyError', 'IndexError'):
                raise ValueError('unsupported expected exception')
            item['raises'] = entry['raises']
        else:
            item['expected'] = _literal(entry['expected_python'])
            item['expected_source'] = ast.unparse(ast.parse(entry['expected_python'],mode='eval'))
        parsed.append(item)
    return entries, parsed


def evaluate_examples(response, draft, snapshot, target, *, checker=check_code):
    """Stable feedback omits traceback paths, timings and hidden evaluator data."""
    try:
        entries, examples = parse_examples(response, (snapshot / target).read_text(encoding='utf-8'))
    except (ValueError, SyntaxError, TypeError, RecursionError) as exc:
        return {'valid': False, 'feedback': 'Public examples could not be parsed: ' + str(exc),
                'examples': [], 'test_sha256': None, 'outcomes': []}
    module = Path(target).with_suffix('').as_posix().replace('/', '.')
    if not all(part.isidentifier() for part in module.split('.')):
        raise ValueError('target module path is not importable')
    lines = [f'import {module} as candidate', 'class PublicExamples(unittest.TestCase):']
    for i, example in enumerate(examples):
        lines += [f'    def test_example_{i}(self):', f'        args = ({example["args_source"]})']
        invocation = f'candidate.{example["function"]}(*args)'
        if 'raises' in example:
            lines += [f'        with self.assertRaises({example["raises"]}):', f'            {invocation}']
        else:
            lines += [f'        self.assertEqual({invocation}, ({example["expected_source"]}))']
    test_source = '\n'.join(lines) + '\n'
    with tempfile.TemporaryDirectory(prefix='public-examples-') as directory:
        test = Path(directory) / 'examples.py'
        test.write_text(test_source, encoding='utf-8')
        checked = checker(draft, snapshot, target, test)
    reason = checked.get('reason', '')
    outcomes = []
    for i in range(len(examples)):
        match = re.search(rf'^test_example_{i} .*? \.\.\. (ok|FAIL|ERROR|skipped[^\n]*)$', reason, re.M)
        outcomes.append(match.group(1) if match else 'not completed')
    status = 'all passed' if checked['passed'] else 'not all passed'
    feedback = ('MODEL-GENERATED PUBLIC EXAMPLES AND EXECUTION RESULTS. Expected answers may be wrong; '
                'verify them against the public task before changing code. These are not hidden tests.\n'
                + json.dumps(entries, ensure_ascii=False, indent=2)
                + '\nExecution: ' + status + '; ' + ', '.join(f'example {i}: {x}' for i, x in enumerate(outcomes)))
    return {'valid': True, 'examples': entries, 'outcomes': outcomes, 'passed': checked['passed'],
            'test_sha256': hashlib.sha256(test_source.encode()).hexdigest(), 'feedback': feedback}
