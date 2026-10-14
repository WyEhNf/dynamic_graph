"""Source-only retained-first-result continuation review; no runtime launch."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair');D=R/'performance-continuation-plan'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=read(D/'plan.json');old=read(R/'performance-plan/plan.json');failure=read(R/'performance-evidence/report.json')
    assert sha(D/'plan.json')=='63e2fc7a63978c275aabe392ae9ed5cf357efde35f2cceed0d09c6161754932c'
    for name,item in p['files'].items():assert sha(D/name)==item['sha256'] and (D/name).stat().st_size==item['bytes'],name
    assert sha(R/'performance-evidence/report.json')==p['original_first_failure_report_sha256']=='070392af398496ac4884a7889bf0b65017c1d4231a6387dc986a30d8e7b06804'
    assert sha(R/'performance-plan/plan.json')==p['original_first_failure_plan_sha256']=='04d73f41e492f90033bf600470f5d724868ab639765a8a1e44abb6fb29811907'
    assert len(failure['records'])==1 and failure['records'][0]['actual_exitcode']==0
    assert p['cases']==old['cases'] and p['runtime']==old['runtime'] and p['schedule']==old['schedule'][1:]
    assert len(p['schedule'])==189 and p['records']==190 and p['pairs']==95
    for item in p['inherited_first_row_files'].values():assert sha(item['path'])==item['sha256']
    assert p['interrupted_pair']['identity']=='changed-arithmetic' and p['interrupted_pair']['round']==0
    source=(D/'runner.py').read_text();assert 'expected_not_run=case[\'matrices\']if case[\'default_path_scope\']==\'native-control\'else 0' in source
    assert 'continuous94' in source and "['continuous94']['VM_pairs']==89" in source and "['continuous94']['native_pairs']==5" in source
    # Actually apply the corrected metric validator to the retained raw record.
    sys.path.insert(0,str(D));import runner
    runner.validate_metric(failure['records'][0]['metric'],failure['records'][0]['case'],failure['records'][0]['backend'])
    assert not (R/'performance-continuation-evidence').exists()
    result=dict(passed=True,source_only=True,plan_sha256=sha(D/'plan.json'),source_files=len(p['files']),first_runtime_record_reused=1,new_launches=189,planned_pairs=95,continuous_pairs=94,continuous_VM_pairs=89,continuous_native_pairs=5,original_failure_preserved=True,corrected_validator_applied_to_actual_first_metric=True,scope='Only fixedVM/not-run classification and explicit interrupted firstpair accounting revised; exact19 originalC/samea95 unchanged. Every planned ratio/negative remains; one noncontiguous firstpair is diagnostic, never represented as a continuous benchmark.',authorized_next='One remaining189 actual execution batch after27 observer terminal; no firstrow relaunch/retry/default changes.')
    (ROOT/'outputs/stage2-root-load-pair-cost-continuation-source.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
