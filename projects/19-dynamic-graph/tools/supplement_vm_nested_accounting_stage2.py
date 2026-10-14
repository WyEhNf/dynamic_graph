"""Freeze an accounting-only revision without compilation or VM execution."""
import hashlib,json,shutil
from pathlib import Path

P=Path(__file__).resolve().parents[1]
STAGE=P/'artifacts/stage2-vm-nested-budget'
INITIAL=STAGE/'initial-freeze'
WORK=STAGE/'component-work/source'
OUT=STAGE/'accounting-supplement'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    old=json.loads((INITIAL/'plan.json').read_text(encoding='utf-8'))
    assert sha(INITIAL/'plan.json')=='cd048c2e441f3d07e8198be5d9a466d753ad0add2b4e5a144565407493b5898a'
    for relative,record in old['frozen_files'].items():assert sha(INITIAL/relative)==record['sha256']
    assert sha(P/'src/vm_step_bound.cpp')=='c761fee9c8d9aa9b2c1cc6ee1caf6ce6704290b89e56bb59d7851d7f3f31e62c'
    assert sha(P/'build/cholesky_runtime.exe')==old['ordinary_sha256'] and sha(P/'build-memory/cholesky_runtime.exe')==old['memory_sha256']
    OUT.mkdir(exist_ok=False);files={}
    for source in sorted(WORK.rglob('*')):
        if not source.is_file():continue
        relative=Path('candidate-source')/source.relative_to(WORK)
        prior=old['frozen_files'][relative.as_posix()]['sha256']
        if relative.suffix!='.cpp' or relative.parts[1]!='src':assert sha(source)==prior
        target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        files[relative.as_posix()]={'before_sha256':prior,'sha256':sha(target),'origin':str(source),'changed':sha(target)!=prior}
    assert [name for name,row in files.items()if row['changed']]==['candidate-source/src/vm_nested_step_bound.cpp']
    command=[part.replace(str(INITIAL/'candidate-source'),str(OUT/'candidate-source'))for part in old['compile_command']]
    table=[
        {'operation':'dom.assign full boolean matrix','charge':'(size+1)^2 before allocation','status':'unchanged'},
        {'operation':'dom[k]=reachable row copy for reachable k>0','charge':'size+1 before each copy','status':'added'},
        {'operation':'auto next=reachable in each dominator iteration','charge':'size+1 before copy','status':'unchanged'},
        {'operation':'each predecessor row intersection','charge':'size+1 before bit scan','status':'unchanged'},
        {'operation':'next!=dom[k] equality comparison','charge':'size+1 before each complete row comparison','status':'added'},
        {'operation':'dom[k]=move(next) replacement','charge':'size+1 before each replacement, conservative full-row charge','status':'added'},
        {'operation':'loop.exits sort comparator','charge':'1 before every less-than comparison','status':'added'},
        {'operation':'loop.exits unique comparator','charge':'1 before every equality comparison','status':'added'},
        {'operation':'summary guard State copy','charge':'1+slot_count+stack_count on entry before guard copy','status':'unchanged'},
        {'operation':'summary result State copy','charge':'1+slot_count+stack_count immediately before independent result copy','status':'added'},
        {'operation':'summary body-entry State copy','charge':'1+slot_count+stack_count before entry copy','status':'unchanged'}]
    target=OUT/'plan-source/tools'/Path(__file__).name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(__file__,target)
    data={'schema':'isolated-nested-VM-accounting-supplement-v1','status':'predeclared accounting revision; no compile or execution','passed_static_freeze':True,'initial_plan_sha256':sha(INITIAL/'plan.json'),'initial_files_retained_unchanged':True,'candidate_files':files,'supplement_producer_sha256':sha(target),'charge_table':table,'compile_command':command,'compiler':old['compiler'],'compile_flags':old['compile_flags'],'dependency_freeze':str(INITIAL/'dependencies'),'ABI':old['ABI'],'original_dependency_files_sha256':{name:record['sha256']for name,record in old['frozen_files'].items()if name.startswith('dependencies/')},'work_limit':250000,'algorithm_unchanged':True,'golden_plan':old['golden_plan'],'minimum_launch_RAM_bytes':old['minimum_launch_RAM_bytes'],'minimum_F_free_bytes':old['minimum_F_free_bytes'],'future_compile_environment':old['future_compile_environment'],'compiler_started':False,'C_execution_started':False,'VM_execution_started':False,'cost_measured':False,'ordinary_sha256':old['ordinary_sha256'],'memory_sha256':old['memory_sha256'],'runtime_or_default_changed':False}
    (OUT/'plan.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({'prepared':True,'supplement_sha256':sha(OUT/'plan.json'),'candidate_CPP_sha256':sha(OUT/'candidate-source/src/vm_nested_step_bound.cpp'),'candidate_test_sha256':sha(OUT/'candidate-source/tests/vm_nested_step_bound_tests.cpp'),'initial_files_unchanged':True,'no_compile_or_VM_execution':True}))

if __name__=='__main__':main()
