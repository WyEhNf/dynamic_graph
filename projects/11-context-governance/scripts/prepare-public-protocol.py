"""Prepare an isolated public-contract protocol; never edit a measured package."""
import ast
import hashlib
import json
from pathlib import Path
import time

root = Path(__file__).resolve().parents[1]
original = root / 'src/context_governance'
destination = root / 'adapters/research-v21/context_governance'
if destination.exists():
    raise FileExistsError(destination)
destination.mkdir(parents=True)
baseline = {}
for source in original.glob('*.py'):
    baseline[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    (destination / source.name).write_bytes(source.read_bytes())


def change(name, old, new):
    path = destination / name
    text = path.read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise ValueError(f'{name}: expected one exact replacement')
    path.write_text(text.replace(old, new), encoding='utf-8')


change('public_examples.py', 'def parse_examples(response, target_source):', '''def declared_functions(target_source, public_task=None):
    functions = {n.name for n in ast.parse(target_source).body
                 if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')}
    if public_task is not None:
        # Only the explicit English public API declaration, not prose mentions
        # or model code. This supports a comment-only new-function placeholder.
        functions.update(name for name in re.findall(
            r'(?m)^\\s*Implement\\s+([A-Za-z_]\\w*)\\s*\\(', public_task)
                         if not name.startswith('_'))
    return functions


def parse_examples(response, target_source, public_task=None):''')
change('public_examples.py', '''    functions = {n.name for n in ast.parse(target_source).body
                 if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')}
    parsed = []''', '''    functions = declared_functions(target_source, public_task)
    parsed = []''')
change('public_examples.py', "raise ValueError('function must be present in the public target file')",
       "raise ValueError('function must be present in the public target file' if public_task is None else 'function must be declared by the public target or task')")
change('public_examples.py', '''        if not isinstance(args, tuple) or len(args) > 12:
            raise ValueError('args_python must be a tuple with at most twelve arguments')''', '''        allow_list = public_task is not None
        if not isinstance(args, (tuple, list) if allow_list else tuple) or len(args) > 12:
            raise ValueError('args_python must be a tuple with at most twelve arguments' if public_task is None else 'args_python must be a tuple or declared-protocol list with at most twelve arguments')''')
change('public_examples.py', 'def evaluate_examples(response, draft, snapshot, target, *, checker=check_code):',
       'def evaluate_examples(response, draft, snapshot, target, *, checker=check_code, public_task=None):')
change('public_examples.py', "entries, examples = parse_examples(response, (snapshot / target).read_text(encoding='utf-8'))",
       "entries, examples = parse_examples(response, (snapshot / target).read_text(encoding='utf-8'), public_task)")

change('local_model.py', '''    def examples_prompt(self, context, task):
        return self.tokenizer.apply_chat_template([''', '''    def examples_prompt(self, context, task, target_source='', protocol='literal-v17'):
        if protocol == 'public-contract-v21':
            from .public_examples import declared_functions
            names = sorted(declared_functions(target_source, task))
            declarations = re.findall(r'(?m)^\\s*Implement\\s+([A-Za-z_]\\w*)\\s*\\([^)]*\\)', task)
            required = [name for name in declarations if name in names]
            allowed = required or names
            import json
            schema = {'function': allowed[0] if allowed else 'PUBLIC_FUNCTION',
                      'args_python': '[3]', 'expected_python': '6'}
            system = ('Generate one to three small examples using ONLY the public task and context. '
                      'The target may be a comment-only placeholder: the public task declares the function to create. '
                      'Return ONLY a JSON array, with no prose or code fence. Every object has function and args_python, '
                      'and exactly one of expected_python or raises. The function must be one of the allowed names. '
                      'args_python is a JSON STRING containing a Python LIST of positional arguments: [] for no arguments, '
                      '[42] for one, [42, 5] for two. Nested tuple/dictionary literals are allowed inside that list. '
                      'expected_python is a JSON STRING containing the exact Python literal result, including tuples where required. '
                      'raises must be ValueError, TypeError, KeyError or IndexError. No Python expressions, calls, or variable references. '
                      'Choose normal and explicitly required invalid-input/empty/ordering examples; derive expectations carefully. '
                      'You cannot see a draft, hidden tests or an oracle. '
                      'FORMAT ONLY (not an actual example): ' + json.dumps([schema]))
            user = ('ALLOWED FUNCTION NAMES: ' + json.dumps(allowed) +
                    '\\nPUBLIC TARGET FILE BEFORE IMPLEMENTATION:\\n' + target_source +
                    '\\nCONTEXT:\\n' + context + '\\nPUBLIC TASK:\\n' + task)
            return self.tokenizer.apply_chat_template([
                {'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                tokenize=False, add_generation_prompt=True)
        if protocol != 'literal-v17':
            raise ValueError('Unknown public-example protocol')
        return self.tokenizer.apply_chat_template([''')
change('run_local_eval.py', "    parser.add_argument('--contract-feedback'", "    parser.add_argument('--public-examples-protocol',choices=['literal-v17','public-contract-v21'],default='literal-v17')\n    parser.add_argument('--contract-feedback'")
change('run_local_eval.py', "              'warmup_generation_calls':3,", "              'public_examples_protocol':args.public_examples_protocol if args.public_example_review else None,\n              'warmup_generation_calls':3,")
change('run_local_eval.py', 'examples_prompt=model.examples_prompt(context,spec)',
       "examples_prompt=model.examples_prompt(context,spec,(snapshot/metadata['target_file']).read_text(encoding='utf-8'),args.public_examples_protocol)")
change('run_local_eval.py', "public_result=evaluate_examples(examples.output,draft.output,snapshot,metadata['target_file'])",
       "public_result=evaluate_examples(examples.output,draft.output,snapshot,metadata['target_file'],public_task=spec if args.public_examples_protocol=='public-contract-v21' else None)")
change('verify_recorded_eval.py', 'examples_prompt=LocalModel.examples_prompt(owner,context,spec)',
       "examples_prompt=LocalModel.examples_prompt(owner,context,spec,(root/metadata['target_file']).read_text(encoding='utf-8'),report.get('public_examples_protocol') or 'literal-v17')")
change('verify_recorded_eval.py', "public_result=evaluate_examples(examples['output'],run['draft']['output'],root,metadata['target_file'],checker=check_code)",
       "public_result=evaluate_examples(examples['output'],run['draft']['output'],root,metadata['target_file'],checker=check_code,public_task=spec if report.get('public_examples_protocol')=='public-contract-v21' else None)")

candidate = {}
for source in destination.glob('*.py'):
    ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    candidate[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
manifest = {'prepared_unix': time.time(), 'baseline_source_sha256': baseline,
            'candidate_source_sha256': candidate,
            'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope': 'Isolated candidate, no tests or quality claim. Public-contract declaration and list argument container '
                     'repair new-function placeholder compatibility. literal-v17 remains the default protocol; old behavior '
                     'and old recorded feedback must still reproduce. English Implement f(args) declaration scope only.'}
(destination.parent / 'provenance.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({'prepared': str(destination), 'modules': len(candidate), 'tested': False}))
