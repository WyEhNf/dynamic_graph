"""Create an isolated Compiler API reuse candidate, keeping the default intact."""
from pathlib import Path
import hashlib
import json
import time

root=Path(__file__).resolve().parents[1]
adapter=root/'adapters'/'typescript'
source=adapter/'worker.mjs'
destination=adapter/'research-candidates-v18'
destination.mkdir(exist_ok=False)
original=source.read_text(encoding='utf-8')
(destination/'baseline.mjs').write_text(original,encoding='utf-8')
changed=original.replace('let previousKey, previousResult;',
    'let previousKey, previousResult;\nlet previousCompileSession;')
changed=changed.replace('getSourceFile(name, languageVersion) {',
    'getSourceFile(name, languageVersion, onError, shouldCreateNewSourceFile) {')
old="if (!sourceFiles.has(name)) sourceFiles.set(name, ts.createSourceFile(name, files.get(name), languageVersion, true, name.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS));"
new="""if (!sourceFiles.has(name)) {
        const prior = previousCompileSession;
        const reused = !shouldCreateNewSourceFile && prior?.files.get(name) === files.get(name) ? prior.sourceFiles.get(name) : undefined;
        sourceFiles.set(name, reused ?? ts.createSourceFile(name, files.get(name), languageVersion, true, name.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS));
      }"""
assert old in changed
changed=changed.replace(old,new)
changed=changed.replace('getDefaultLibFileName:',
    'hasInvalidatedResolutions: () => true, // Resolve every import against the new virtual snapshot.\n    getDefaultLibFileName:')
old='moduleResolution: ts.ModuleResolutionKind.Bundler}, host);'
assert old in changed
changed=changed.replace(old,'moduleResolution: ts.ModuleResolutionKind.Bundler}, host, previousCompileSession?.program);\n  for (const filename of files.keys()) sourceFiles.set(filename, program.getSourceFile(filename));')
old='  return result;\n}'
assert old in changed
changed=changed.replace(old,'  previousCompileSession = {files, sourceFiles, program};\n  return result;\n}')
(destination/'incremental.mjs').write_text(changed,encoding='utf-8')
manifest={'frozen_unix':time.time(),'scope':'Isolated candidate only, default worker unchanged; unchanged SourceFile reuse with oldProgram, import resolution invalidated every request.',
          'compiler_version':'6.0.3','sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.glob('*.mjs')},
          'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(destination/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest))
