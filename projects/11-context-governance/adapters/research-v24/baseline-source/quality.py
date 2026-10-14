"""Functional checks of generated files in disposable local snapshot copies."""
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def extract_code(response):
    blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', response, re.S | re.I)
    return max(blocks, key=len) if blocks else response.strip()


def check_code(response, root: Path, target: str, test_file: Path):
    code = extract_code(response)
    try:
        tree = ast.parse(code)
        allowed = {'math', 'collections', 're', 'decimal', 'typing', 'itertools', 'copy', 'heapq', 'config', 'helpers'}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [n.name.split('.')[0] for n in node.names] if isinstance(node, ast.Import) else [(node.module or '').split('.')[0]]
                if any(name not in allowed for name in names):
                    raise ValueError('import outside fixture allowlist')
            if isinstance(node, ast.Name) and node.id in {'open', 'exec', 'eval', 'compile', '__import__', '__builtins__', 'breakpoint', 'globals', 'locals', 'getattr', 'setattr', 'delattr', 'vars'}:
                raise ValueError('unsafe generated operation')
            if isinstance(node, ast.Attribute) and node.attr.startswith('__'):
                raise ValueError('dunder introspection disallowed')
            if isinstance(node, ast.Attribute) and node.attr in {'sys','os','modules','builtins','environ'}:
                raise ValueError('framework/process introspection disallowed')
            if isinstance(node, ast.Attribute) and isinstance(node.ctx,(ast.Store,ast.Del)):
                raise ValueError('attribute mutation outside pure-function fixture contract')
    except (SyntaxError, ValueError) as exc:
        return {'passed': False, 'reason': str(exc), 'code': code}
    with tempfile.TemporaryDirectory(prefix='hackathon11-') as temporary:
        directory = Path(temporary)
        shutil.copytree(root, directory / 'repo')
        (directory / 'repo' / target).write_text(code, encoding='utf-8')
        dependencies = {p.relative_to(directory/'repo').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (directory/'repo').rglob('*') if p.is_file() and p.relative_to(directory/'repo').as_posix()!=target}
        test = test_file.read_text(encoding='utf-8')
        expected_tests = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(ast.parse(test)))
        if expected_tests==0: raise ValueError('trusted fixture contains no tests')
        nonce = uuid.uuid4().hex
        driver = ("import sys, unittest, types, io, json, traceback\n"
                  "sys.path.insert(0, " + repr(str(directory / 'repo')) + ")\n"
                  "evidence={'tests_run':0,'passed':False}\n"
                  "frozen={cls:dict(vars(cls)) for cls in [unittest.TestCase,unittest.TestSuite,unittest.TestLoader,unittest.TextTestRunner,unittest.TextTestResult]}\n"
                  "try:\n"
                  "    module=types.ModuleType('trusted_checks')\n"
                  "    module.__dict__['unittest']=unittest\n"
                  "    exec(" + repr(test) + ",module.__dict__)\n"
                  "    if any(dict(vars(cls))!=state for cls,state in frozen.items()): raise RuntimeError('test framework was mutated')\n"
                  "    suite=unittest.defaultTestLoader.loadTestsFromModule(module)\n"
                  "    stream=io.StringIO()\n"
                  "    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)\n"
                  "    if any(dict(vars(cls))!=state for cls,state in frozen.items()): raise RuntimeError('test framework was mutated')\n"
                  "    evidence={'tests_run':result.testsRun,'passed':result.wasSuccessful() and not result.skipped,'log':stream.getvalue()}\n"
                  "except BaseException as error:\n"
                  "    evidence['log']=traceback.format_exc()\n"
                  "print(" + repr(nonce+':') + "+json.dumps(evidence))\n")
        (directory / 'check.py').write_text(driver, encoding='utf-8')
        try:
            result = subprocess.run([sys.executable, '-I', str(directory / 'check.py')],
                                    cwd=directory, capture_output=True, text=True, timeout=15)
            completion = [line[len(nonce)+1:] for line in result.stdout.splitlines() if line.startswith(nonce+':')]
            evidence = json.loads(completion[-1]) if completion else {'tests_run':0,'passed':False,'log':'missing trusted test completion'}
            unchanged = all((directory/'repo'/name).exists() and hashlib.sha256((directory/'repo'/name).read_bytes()).hexdigest()==digest for name,digest in dependencies.items())
            passed = result.returncode==0 and evidence['passed'] and evidence['tests_run']==expected_tests and unchanged
            return {'passed':bool(passed),'tests_run':evidence['tests_run'],'expected_tests':expected_tests,
                    'dependencies_unchanged':unchanged, 'reason':str(evidence.get('log',''))[-4000:], 'code':code}
        except subprocess.TimeoutExpired:
            return {'passed': False, 'reason': 'functional test timed out', 'code': code}
