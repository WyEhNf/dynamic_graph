"""Correct overstrict helper call checks without changing frozen v26 evidence.

Public specs saying call for each input do not imply exactly once or a helper
call order. Only cache_trace explicitly demands checked_capacity exactly once.
This revision relaxes helper call list equality to multiplicity coverage.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'adapters'/'correctness-v26'
NEW=ROOT/'adapters'/'correctness-v27'
SUITE=ROOT/'fixtures'/'combined-public-v17'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

class RelaxHelperCalls(ast.NodeTransformer):
    changed=0
    def visit_Call(self,node):
        self.generic_visit(node)
        if (isinstance(node.func,ast.Attribute) and node.func.attr=='assertEqual' and len(node.args)==2
            and isinstance(node.args[0],ast.ListComp)
            and any(isinstance(n,ast.Attribute) and n.attr=='call_args_list' for n in ast.walk(node.args[0]))):
            self.changed+=1
            return ast.copy_location(ast.Call(func=ast.Attribute(value=node.func.value,attr='assertFalse',ctx=ast.Load()),
                args=[ast.BinOp(left=ast.Call(func=ast.Name(id='Counter',ctx=ast.Load()),args=[node.args[1]],keywords=[]),
                                op=ast.Sub(),right=ast.Call(func=ast.Name(id='Counter',ctx=ast.Load()),args=[node.args[0]],keywords=[]))],keywords=[]),node)
        return node

def main():
    old_manifest=json.loads((OLD/'all30-contract-manifest.json').read_text(encoding='utf-8'))
    (NEW/'public_contracts').mkdir(parents=True,exist_ok=True)
    cases={}
    changed=[]
    for case_id,entry in old_manifest['cases'].items():
        old=OLD/'public_contracts'/f'{case_id}.py'
        if sha(old)!=entry['test_sha256']: raise ValueError('frozen v26 public contract changed')
        tree=ast.parse(old.read_text(encoding='utf-8'))
        rewrite=RelaxHelperCalls()
        tree=rewrite.visit(tree)
        if rewrite.changed:
            if not any(isinstance(n,ast.ImportFrom) and n.module=='collections' and any(a.name=='Counter' for a in n.names) for n in tree.body):
                tree.body.insert(0,ast.ImportFrom(module='collections',names=[ast.alias(name='Counter')],level=0))
            changed.append(case_id)
        ast.fix_missing_locations(tree)
        source=ast.unparse(tree)+'\n'
        compile(source,f'{case_id}.py','exec')
        new=NEW/'public_contracts'/f'{case_id}.py'
        if new.exists() and new.read_text(encoding='utf-8')!=source: raise ValueError('refuse changing frozen v27 tests')
        if not new.exists(): new.write_text(source,encoding='utf-8')
        cases[case_id]={'spec_sha256':entry['spec_sha256'],'test_sha256':sha(new),
                       'v26_test_sha256':entry['test_sha256'],'relaxed_helper_assertions':rewrite.changed}
    protocol=NEW/'protocol.py'
    data=(OLD/'protocol.py').read_bytes()
    if protocol.exists() and protocol.read_bytes()!=data: raise ValueError('refuse changing protocol')
    if not protocol.exists(): protocol.write_bytes(data)
    manifest={'version':'public-contracts-all30-v27','origin':'Public-spec derived development-informed DEV finite tests; not holdout/full-domain proof/official score',
              'revision_reason':'Remove unsupported exactly-once/order constraints for helpers except explicitly specified capacity helper',
              'source_v26_manifest_sha256':sha(OLD/'all30-contract-manifest.json'),
              'script_sha256':sha(Path(__file__)),'protocol_sha256':sha(protocol),
              'suite_manifest_sha256':sha(SUITE/'manifest.json'),'cases':cases}
    path=NEW/'contract-manifest.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=manifest: raise ValueError('frozen v27 manifest differs')
    if not path.exists(): path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(cases),'relaxed_cases':changed,'manifest_sha256':sha(path)}))

if __name__=='__main__': main()
