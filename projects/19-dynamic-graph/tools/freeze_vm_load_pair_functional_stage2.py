"""Freeze completed54 observer functionality, without any new execution."""
import hashlib,json,shutil
from pathlib import Path
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()
def main():
    report=json.loads((R/'functional-evidence/report.json').read_text());assert report['passed']
    assert len(report['records'])==54 and len(report['pairs'])==27
    out=R/'functional-acceptance';assert not out.exists();out.mkdir()
    origins={}
    def copy(origin,relative):
        dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin,dest);origins[relative]=origin
    for directory in ['functional-plan','functional-plan-resource-supplement','functional-evidence']:
        for p in sorted((R/directory).rglob('*')):
            if p.is_file():copy(p,directory+'/'+p.relative_to(R/directory).as_posix())
    # Freeze original small C/harness/meta/oracle EXE sources; large prior input/oracle
    # streams remain immutable at their recorded paths with54 freshly checked hashes.
    for row in report['records']:
        c=row['case']
        for name in ['source.c','oracle.c','program.meta','oracle.exe']:
            rel='references/'+c['identity']+'/'+name
            if rel not in origins:copy(Path(c['paths'][name]),rel)
    copy(Path(__file__),'freeze-producer.py')
    files={}
    for relative,origin in origins.items():
        p=out/relative;digest=sha(p);assert digest==sha(origin)
        files[relative]={'origin':str(origin),'sha256':digest,'bytes':p.stat().st_size}
    manifest={'schema':'load-pair-realC-functional-acceptance-v1','passed':True,'records':54,'pairs':27,
              'functional_plan_sha256':report['plan_sha256'],'actual_report_sha256':sha(R/'functional-evidence/report.json'),
              'observer_exe_sha256':report['observer_EXE_sha256'],'a95_performance_exe':'not run in this functional gate',
              'matching_core_sha256':'87414eef783a1ea7122458ab4faa0807fd7598f36be2438501a2febe9b0b8e88',
              'matching_header_sha256':'65918905ae87a751b9745bdbf9aae3c5f26644b5aecefbb279731b173fedc3d4',
              'complete_originalC_bytes':sum(r['wholeC_comparison']['bytes_compared']for r in report['records']),
              'per_matrix_contract':'real metrics steps/PC/engine/error equality; native actual PC marked not applicable; observer time not performance',
              'all_reference_stream_hashes':'all54 launches freshly checked each original source/harness/oracleEXE/meta/input/oracle; recorded original paths retained, no new C generation',
              'resource_gates':len(report['resource_gate_observations']),
              'performance_or_default_changes':False,'files':files}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'manifest':str(out/'manifest.json'),'sha256':sha(out/'manifest.json'),'frozen_files':len(files),
                      'wholeC_bytes':manifest['complete_originalC_bytes']}),flush=True)
if __name__=='__main__':main()
