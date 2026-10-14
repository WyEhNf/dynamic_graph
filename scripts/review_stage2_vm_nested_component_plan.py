"""Audit immutable initial plan and accounting-only supplement before execution."""
import difflib
import hashlib
import json
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/19-dynamic-graph'
D=P/'artifacts/stage2-vm-nested-budget'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    initial=D/'initial-freeze'; supplement=D/'accounting-supplement'
    old=read(initial/'plan.json');new=read(supplement/'plan.json')
    assert sha(initial/'plan.json')==new['initial_plan_sha256']=='cd048c2e441f3d07e8198be5d9a466d753ad0add2b4e5a144565407493b5898a'
    for name,row in old['frozen_files'].items():assert sha(initial/name)==row['sha256']
    for name,digest in new['original_dependency_files_sha256'].items():assert sha(initial/name)==digest
    for name,row in new['candidate_files'].items():
        assert sha(initial/name)==row['before_sha256'] and sha(supplement/name)==row['sha256']
        assert row['changed']==name.endswith('vm_nested_step_bound.cpp')
    assert new['ABI']==old['ABI'] and new['work_limit']==old['algorithm']['work_limit']==250000
    assert new['golden_plan']==old['golden_plan']
    gold=new['golden_plan'];assert (gold['expected_total_counted_goldens'],gold['boundary_contracts'],gold['planned_single_position_mutations'])==(1081,2162,16320)
    assert new['compile_flags']==old['compile_flags']
    assert sha(Path(new['compiler']['path']))==new['compiler']['sha256']
    oldcommand=old['compile_command'];command=new['compile_command']
    assert len(command)==len(oldcommand)
    changes=[]
    for before,after in zip(oldcommand,command):
        if before!=after:
            assert after==before.replace(str(initial/'candidate-source'),str(supplement/'candidate-source'))
            changes.append((before,after))
    assert len(changes)==3
    source='candidate-source/src/vm_nested_step_bound.cpp'
    before=(initial/source).read_text();after=(supplement/source).read_text()
    diff=list(difflib.unified_diff(before.splitlines(True),after.splitlines(True)))
    # Review bounded patches: no algorithm or opcode semantics changes.
    assert sum(line.startswith('@@') for line in diff)==3
    assert len(new['charge_table'])==11
    for fragment in ('else{meter.tick(size+1);dom[k]=reachable;}',
                     'next[k]=true;meter.tick(size+1);',
                     'if(next!=dom[k]){meter.tick(size+1);',
                     '[&](auto a,auto b){meter.tick();return a<b;}',
                     '[&](auto a,auto b){meter.tick();return a==b;}',
                     'charge_state(input,meter);State result=input;'):
        assert fragment in after and fragment not in before
    for name in ('ordinary_sha256','memory_sha256'):
        assert old[name]==new[name]
    assert sha(P/'build/cholesky_runtime.exe')==new['ordinary_sha256']
    assert not any(new[k] for k in ('compiler_started','VM_execution_started','C_execution_started','cost_measured','runtime_or_default_changed'))
    result=dict(passed=True,reviewed_unix=time.time(),initial_plan_sha256=sha(initial/'plan.json'),supplement_plan_sha256=sha(supplement/'plan.json'),
        original_frozen_files=len(old['frozen_files']),accounting_diff_hunks=3,charge_table_rows=11,compile_command_replacements=3,
        planned_goldens=1081,planned_boundaries=2162,planned_mutations=16320,actual_component_execution_count=0,
        scope='Static source/CFG/forest/interval and conservative nested original-opcode cost design reviewed. Accounting-only supplement preserves initial freeze, algorithm, gold denominator, accepted da955/57205 ABI,250k work and production default. Compile/small VM tests still required; not universal proof or performance result.')
    target=ROOT/'outputs/stage2-root-vm-nested-component-plan.json';target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
