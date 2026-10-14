"""Optional persistent TypeScript compiler worker; no source execution."""
import json
import shutil
import subprocess
import threading
from pathlib import Path

from .core import Item


class TypeScriptContext:
    def __init__(self, node=None, *, worker_path=None):
        runtime = node or shutil.which('node')
        if not runtime:
            raise RuntimeError('Node.js is required for the optional TypeScript adapter')
        adapter_root = Path(__file__).resolve().parents[2] / 'adapters/typescript'
        worker = Path(worker_path) if worker_path else adapter_root / 'worker.mjs'
        if not (adapter_root / 'node_modules/typescript/package.json').exists():
            raise RuntimeError('Install pinned adapter dependencies: npm ci in adapters/typescript')
        self.process = subprocess.Popen([str(runtime), str(worker)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1)
        self._lock = threading.Lock()

    def analyze(self, files, pinned_files=(), *, use_cache=True):
        with self._lock:
            if self.process.poll() is not None:
                raise RuntimeError('TypeScript worker exited: ' + self.process.stderr.read()[-2000:])
            self.process.stdin.write(json.dumps({'files': files, 'pinned_files': list(pinned_files), 'use_cache': bool(use_cache)}, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError('TypeScript worker returned no response')
            response = json.loads(line)
            if not response['ok']:
                raise ValueError(response['error'])
            result = response['result']
            result['items'] = tuple(Item(**item) for item in result['items'])
            return result

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=10)
        for stream in (self.process.stdout, self.process.stderr):
            if stream:
                stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
