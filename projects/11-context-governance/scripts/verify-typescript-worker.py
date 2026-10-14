"""Run the existing compiler/Node semantic suite against an isolated worker."""
import argparse
import functools
import hashlib
import importlib.util
import json
import time
import unittest
from pathlib import Path

from context_governance.typescript_context import TypeScriptContext

parser=argparse.ArgumentParser()
parser.add_argument('--worker',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
worker=Path(args.worker).resolve()
test_file=root/'tests/test_typescript_context.py'
spec=importlib.util.spec_from_file_location('worker_semantic_tests',test_file)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.TypeScriptContext=functools.partial(TypeScriptContext,worker_path=worker)
started=time.time()
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
record={'worker':str(worker),'worker_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),
        'test_sha256':hashlib.sha256(test_file.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skipped':len(result.skipped),'successful':result.wasSuccessful(),
        'wall_seconds':time.time()-started,'scope':'Existing five semantic tests use the isolated worker; actual TypeScript compiler and Node execute selected source. No model code is evaluated.'}
Path(args.output).write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
raise SystemExit(0 if result.wasSuccessful() and result.testsRun==5 and not result.skipped else 1)
