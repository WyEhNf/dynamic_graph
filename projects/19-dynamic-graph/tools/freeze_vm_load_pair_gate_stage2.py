"""Freeze completed isolated gate, including all CTest pipeline lineage."""
import hashlib,json,shutil
from pathlib import Path
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
P=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        while block:=f.read(1048576):h.update(block)
    return h.hexdigest()
def main():
    report=json.loads((R/'build-gate-continuation-evidence/report.json').read_text());assert report['passed']
    out=R/'build-gate-acceptance';assert not out.exists();out.mkdir()
    for name in ['source-before','workspace','baseline-build','review-supplement','build-gate-plan','build-gate-evidence','build-gate-continuation-plan','build-gate-continuation-evidence']:
        shutil.copytree(R/name,out/name)
    for label in ['gnu','portable','disabled']:
        root=R/('build-'+label)
        for file in root.rglob('*'):
            if file.is_file()and(file.suffix in ['.exe','.a','.make','.rsp']or file.name in ['CMakeCache.txt','link.txt','CTestTestfile.cmake','LastTest.log']):
                dest=out/('build-'+label)/file.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest)
    for name in ['manifest.json','implementation.diff','producer.py','original-counterexamples.json']:
        shutil.copyfile(R/name,out/('source-only-'+name))
    shutil.copyfile(Path(__file__),out/'freeze-producer.py')
    files={}
    for p in sorted(out.rglob('*')):
        if not p.is_file():continue
        relative=p.relative_to(out).as_posix()
        if relative=='freeze-producer.py':origin=Path(__file__)
        elif relative.startswith('source-only-'):origin=R/relative[len('source-only-'):]
        else:origin=R/relative
        assert origin.exists()and sha(origin)==sha(p),relative
        files[relative]={'sha256':sha(p),'bytes':p.stat().st_size,'origin':str(origin)}
    manifest={'schema':'load-pair-isolated-three-build-gate-acceptance-v1','passed':True,'source_manifest_sha256':sha(R/'manifest.json'),
              'continuation_plan_sha256':sha(R/'build-gate-continuation-plan/plan.json'),
              'first_failure_report_sha256':sha(R/'build-gate-evidence/report.json'),
              'actual_passed_report_sha256':sha(R/'build-gate-continuation-evidence/report.json'),
              'failure_preserved':'first runner exit1 expected15 vs actual14 CTest; candidate unchanged; reused GNU successful gate without rerun',
              'counts':{'GNU_CTest':14,'portable_CTest':14,'disabled_CTest':13,'enabled_new_comparisons_each':8464,'original_comparisons_each':934},
              'source_and_ABI':'All three cores+callers rebuilt with same6591 metrics header; never old baseline library linked.',
              'build_flags':'original frozen future commands, proof/nestedOFF; VECTOR_SCANS/PANEL remain source defaultOFF, not baseline844 ON; no performance comparison to844 claimed.',
              'CLI':'GNU new explicit has actual fused pairs; portable explicit actual decoded-fallback/portable-fallback; disabled rejects exact error/no output; auto unchanged, three complete80byte outputs equal each enabled build.',
              'no_perf_fullC_maximum_or_default_promotion':True,'ordinary_sha256':sha(P/'build/cholesky_runtime.exe'),
              'memory_sha256':sha(P/'build-memory/cholesky_runtime.exe'),'files':files}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'passed':True,'manifest':str(out/'manifest.json'),'sha256':sha(out/'manifest.json'),'frozen_files':len(files),
                      'bytes':sum(v['bytes']for v in files.values())}),flush=True)
if __name__=='__main__':main()
