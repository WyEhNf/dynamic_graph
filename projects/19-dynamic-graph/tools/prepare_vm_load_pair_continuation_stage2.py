"""Freeze runner-only continuation; never change candidate or initial evidence."""
import hashlib,json,shutil,difflib
from pathlib import Path
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    out=R/'build-gate-continuation-plan';assert not out.exists();out.mkdir()
    old=R/'build-gate-plan';report=read(R/'build-gate-evidence/report.json');plan=read(old/'plan.json')
    assert report['first_failure']['message']=="('gnu', 'CTest denominator')"and len(report['records'])==3
    assert all(r['actual_exitcode']==0 for r in report['records'])
    original=(old/'runner.py').read_text();candidate=original
    candidate=candidate.replace("directory=R/'build-gate-evidence'","directory=R/'build-gate-continuation-evidence'")
    candidate=candidate.replace("plan=read(R/'build-gate-plan/plan.json')","plan=read(R/'build-gate-continuation-plan/plan.json')")
    candidate=candidate.replace("for path,entry in plan['source_files'].items():assert sha(R/'build-gate-plan'/path)==entry['sha256'],path",
                               "for path,entry in plan['source_files'].items():assert sha(R/'build-gate-continuation-plan'/path)==entry['sha256'],path\n    assert sha(R/'build-gate-evidence/report.json')==plan['initial_report_sha256']\n    inherited=read(R/'build-gate-evidence/report.json')\n    for row in inherited['records']:\n        assert row['actual_exitcode']==0\n        assert sha(Path(row['raw_stdout']))==row['stdout_sha256'] and sha(Path(row['raw_stderr']))==row['stderr_sha256']\n    assert inherited['builds']['gnu']['new_header_sha256']==sha(R/'workspace/include/cholesky/runtime.hpp')\n    for path,entry in inherited['builds']['gnu']['artifacts'].items():assert sha(R/'build-gnu'/path)==entry['sha256'],path")
    candidate=candidate.replace("'plan_sha256':sha(R/'build-gate-plan/plan.json')","'plan_sha256':sha(R/'build-gate-continuation-plan/plan.json'),\n            'initial_report_sha256':plan['initial_report_sha256'],'reused_records':inherited['records']")
    before="""            assert not (R/('build-'+label)).exists(),'new build must be fresh'
            launch(label+'-configure',commands['configure']);launch(label+'-build',commands['build'])"""
    after="""            if label!='gnu':
                assert not (R/('build-'+label)).exists(),'new build must be fresh'
                launch(label+'-configure',commands['configure']);launch(label+'-build',commands['build'])"""
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    before="""            completed=launch(label+'-ctest',commands['ctest'])
            count=15 if label!='disabled'else 14"""
    after="""            if label=='gnu':
                from subprocess import CompletedProcess
                row=inherited['records'][2]
                completed=CompletedProcess(row['command'],0,Path(row['raw_stdout']).read_text(),Path(row['raw_stderr']).read_text())
                report['builds']['gnu']['inherited_CTest_raw_directory']=str(R/'build-gate-evidence')
            else:completed=launch(label+'-ctest',commands['ctest'])
            count=14 if label!='disabled'else 13"""
    assert candidate.count(before)==1;candidate=candidate.replace(before,after)
    (out/'runner.py').write_text(candidate)
    shutil.copyfile(old/'windows_file_resource_probe_stage2.py',out/'windows_file_resource_probe_stage2.py')
    shutil.copyfile(old/'cli.meta',out/'cli.meta');shutil.copyfile(old/'cli.input',out/'cli.input')
    shutil.copyfile(Path(__file__),out/'producer.py')
    (out/'runner.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='original-frozen-runner',tofile='continuation-runner')))
    plan['schema']='isolated-load-pair-runner-only-continuation-v1'
    plan['contract_expectation']['enabled_CTest_count']=14;plan['contract_expectation']['disabled_CTest_count']=13
    plan['initial_plan_sha256']=sha(old/'plan.json');plan['initial_report_sha256']=sha(R/'build-gate-evidence/report.json')
    plan['reuse']='GNU configure/build/14CTest by original actual terminal/raw/core/newheader SHA; no duplicate GNU build/CTest'
    plan['same_commands_and_flags']=True;plan['candidate_and_original_evidence_unchanged']=True
    plan['source_files']={p.name:{'sha256':sha(p),'bytes':p.stat().st_size}for p in out.iterdir()if p.is_file()}
    write(out/'plan.json',plan)
    print(json.dumps({'plan':str(out/'plan.json'),'sha256':sha(out/'plan.json'),'candidate_unchanged':True,'not_run_yet':True}),flush=True)
if __name__=='__main__':main()
