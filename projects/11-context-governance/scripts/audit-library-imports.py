"""Audit stored model imports before revising the pure-function library guard."""
import ast
import hashlib
import json
from pathlib import Path
import time

from context_governance.quality import extract_code

started=time.time(); records=[]; inspected=0
for path in sorted(Path('artifacts').glob('research-model-v*.json')):
    report=json.loads(path.read_text(encoding='utf-8'))
    for case in report.get('cases',[]):
        for mode,runs in case['runs'].items():
            for run in runs:
                phases={'final':run}
                if 'draft' in run: phases['draft']=run['draft']
                for phase,generation in phases.items():
                    inspected+=1
                    try: tree=ast.parse(extract_code(generation['output']))
                    except SyntaxError: continue
                    imported=set()
                    for node in ast.walk(tree):
                        if isinstance(node,ast.Import): imported.update(x.name.split('.')[0] for x in node.names)
                        elif isinstance(node,ast.ImportFrom): imported.add((node.module or '').split('.')[0])
                    relevant=imported & {'copy','heapq'}
                    if relevant:
                        records.append({'report':path.name,'case':case['id'],'mode':mode,'repeat':run['repeat'],
                                        'phase':phase,'imports':sorted(relevant)})
result={'inspected_stored_outputs':inspected,'affected_import_records':records,
        'scope':'Static audit only; does not revise/regrade historical outcomes.',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'finished_unix':time.time(),'wall_seconds':time.time()-started}
Path('artifacts/library-import-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
