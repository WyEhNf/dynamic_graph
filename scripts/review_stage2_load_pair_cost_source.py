"""Source-only matched-binary cost gate, complete functional archive review."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair');D=R/'performance-plan'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    p=read(D/'plan.json');n=read(R/'next-static-plan/plan.json');f=read(R/'functional-acceptance/manifest.json');root=read(ROOT/'outputs/stage2-root-load-pair-functional-actual.json')
    assert sha(D/'plan.json')=='04d73f41e492f90033bf600470f5d724868ab639765a8a1e44abb6fb29811907'
    assert sha(R/'functional-acceptance/manifest.json')=='c4b62d34c8a45cd5befd9f945e4a7117265770be08e4a9873de1d92690e597e9'
    for name,item in f['files'].items():assert sha(R/'functional-acceptance'/name)==sha(item['origin'])==item['sha256'] and (R/'functional-acceptance'/name).stat().st_size==item['bytes']
    assert len(f['files'])==314 and f['actual_report_sha256']==root['report_sha256'] and f['complete_originalC_bytes']==163974808
    for name,item in p['files'].items():assert sha(D/name)==item['sha256'] and (D/name).stat().st_size==item['bytes']
    assert p['cases']==n['cost']['cases'] and p['runtime']==n['runtime'] and len(p['cases'])==19
    assert sha(p['runtime']['path'])==p['runtime']['sha256']=='a95a97d865f7be0942da06b9b35845fd540f88ed05aeaf0bea04d478fbb347e9'
    schedule=[]
    for case in p['cases']:
        assert type(case['expected_vm_steps']) is int and case['expected_vm_steps']>=0
        assert '--max-vm-steps' not in case['runtime_command_common'] and case['runtime_command_common'][-2:]==['--vm-budget','fixed']
        for r in range(5):
            for backend in p['backends'] if r%2==0 else list(reversed(p['backends'])):schedule.append(dict(identity=case['identity'],round=r,backend=backend))
    assert schedule==p['schedule'] and len(schedule)==p['records']==190 and p['pairs']==95
    assert p['genuine_VM_pairs']==90 and p['native_bypass_pairs']==5 and p['output_bytes_predeclared']==817390840
    assert p['functional_gate_required']['plan_sha256']=='bfbbf8634dcad7e6afb49ecf455f5783d916d3d6b71bdc7c3a88c292b21eb981'
    assert not p['observer_used_for_perf'] and not p['amplify_or_select_sources'] and not p['compile_new_C_or_oracle']
    assert not (R/'performance-evidence').exists()
    result=dict(passed=True,source_only=True,cost_plan_sha256=sha(D/'plan.json'),functional_archive_files=314,functional_archive_full_bytes_verified=163974808,source_files=len(p['files']),records=190,pairs=95,genuine_VM_pairs=90,native_control_pairs=5,output_bytes=817390840,review=['Fixed original19 cohort and declared5 alternation; exacta95 onlybackend differs; fixedbudget/proofOFF/noobserver','Fresh immutableEXE/sixCrefs before every launch; whole originalC every record; resourcegate observed and preserved beforeexit75','Actual main compute includes execute_owned/decode/discovery; IO/SHA/comparison/probe processwall separate, no wall-based instruction speed claims','All19 short/negative/tie records retained,90VM/5native separate; topPC unavailable remainsnull rather than inferred'],authorized_next='One frozen190/95 real samebinary cost run; no retries/newC/cohort/default promotion. Preserve all actual terminal/partial evidence.')
    (ROOT/'outputs/stage2-root-load-pair-cost-source.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
