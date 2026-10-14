"""Replay every historical R51 successful-suite record with exact plan equality."""
from pathlib import Path
import ast,hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/Hackathon-stage2-artifacts/project27/20261013/r64/regression');OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT.parent/'build/aicore_bench.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    tree=ast.parse((ROOT/'scripts/regress_current.py').read_text());suites=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='suites' for t in node.targets):suites.extend(ast.literal_eval(node.value))
        if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='suites':suites.extend(ast.literal_eval(node.value))
    suites=[(n,src,f'reports/{n}-batch51.json') for n,src,_ in suites]
    suites.extend([('forkjoin','data/nested-forkjoin-new-batch38.json','reports/forkjoin-candidate-batch51.json'),('shallow-heldout','data/shallow-heldout-batch44.json','reports/shallow-heldout-candidate-batch51.json'),('resource-cliques','data/resource-cliques-batch31.json','reports/resource-cliques-candidate-batch51.json')])
    report={'complete':False,'records':0,'suites':{},'source_sha256':sha(ROOT/'research/batch64/solution.cpp'),'exe_sha256':sha(EXE),'script_sha256':sha(Path(__file__))};start=time.perf_counter()
    for label,source,before in suites:
        src=ROOT/source;old=ROOT/before;dst=OUT/f'{label}.json';failed=OUT/f'{label}-failures.json'
        run=subprocess.run([str(EXE),'--input',str(src),'--output',str(dst),'--failures',str(failed)],capture_output=True,text=True)
        assert run.returncode==0,(label,run.stdout,run.stderr)
        b=json.loads(old.read_text())['cases'];a=json.loads(dst.read_text())['cases'];assert len(a)==len(b)
        for x,y in zip(b,a):
            for key in ('name','pass','valid','T','peak_memory','plan'):assert x[key]==y[key],(label,x['name'],key)
            assert y['models_equal'] and y['pass']
        report['records']+=len(a);report['suites'][label]={'records':len(a),'exact_plans':True,'sha256':{str(p):sha(p) for p in [src,old,dst,failed]}}
        (OUT/'report.partial.json').write_text(json.dumps(report,indent=2));print(label,len(a),'same plans',flush=True)
    assert report['records']==1099
    report.update(complete=True,elapsed_seconds=time.perf_counter()-start);(OUT/'report.json').write_text(json.dumps(report,indent=2));print('1099 exact-plan regressions passed',flush=True)


if __name__=='__main__':main()
