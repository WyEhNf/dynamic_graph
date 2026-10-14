"""Preserve initial preparation; freeze resource rejection observations in new plan."""
import difflib,hashlib,json,shutil
from pathlib import Path
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
OLD=R/'functional-plan';NEW=R/'functional-plan-resource-supplement'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not NEW.exists();shutil.copytree(OLD,NEW)
    original=(OLD/'runner.py').read_text();candidate=original.replace("PLAN=R/'functional-plan'","PLAN=R/'functional-plan-resource-supplement'")
    before="""        value=fresh()
        if min(value['available_RAM_bytes'],value['free_G_bytes'])<ONE:raise SystemExit(75)"""
    after="""        value=fresh()
        value['passed']=min(value['available_RAM_bytes'],value['free_G_bytes'])>=ONE
        report.setdefault('resource_gate_observations',[]).append(value)
        write(EVIDENCE/'report.json',report) # Retain rejected fresh values before exit75.
        if not value['passed']:raise SystemExit(75)"""
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    (NEW/'runner.py').write_text(candidate)
    (NEW/'runner.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='immutable-initial-runner',tofile='resource-supplement-runner')))
    shutil.copyfile(Path(__file__),NEW/'supplement-producer.py')
    plan=json.loads((OLD/'plan.json').read_text());plan['schema']='load-pair-functional-observer-resource-supplement-v1'
    plan['initial_functional_plan_sha256']=sha(OLD/'plan.json')
    plan['resource_only_change']='Record every fresh observed RAM/G threshold decision before exit75, including rejected gates; source54/cohort/observer/core/header/flags unchanged.'
    plan['compile_command']=[x.replace(str(OLD),str(NEW))for x in plan['compile_command']]
    plan['source_files']={p.relative_to(NEW).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(NEW.rglob('*'))if p.is_file()and p.name!='plan.json'}
    (NEW/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'plan':str(NEW/'plan.json'),'sha256':sha(NEW/'plan.json'),'initial_plan_sha256':sha(OLD/'plan.json'),
                      'source_only':True,'actual_compile_C_VM_runs':0,'frozen_files':len(plan['source_files'])}),flush=True)
if __name__=='__main__':main()
