"""Regenerate every accepted old suite Metadata without repeating C/runtime work."""
import hashlib,json,shutil,time
from pathlib import Path
from analyze_source import analyze


def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-default-metadata-audit'
    if root.exists():raise SystemExit('Refusing to overwrite default audit')
    root.mkdir();started=time.perf_counter();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    names=('tools/analyze_source.py','tools/metadata_wire.py','tools/symbolic_metadata.py','tools/audit_default_metadata_stage2.py');hashes={}
    for name in names:
        path=root/'source'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,path);hashes[name]=sha(path)
    roots=[project/'artifacts'/('build-stage2-wire-ctest-'+label) for label in ('pipeline','helpers','while','integer-selectors')]
    reports=sorted(path for folder in roots for path in folder.rglob('*.analysis.json'));rows=[];skips=[]
    for i,path in enumerate(reports):
        old=json.loads(path.read_text(encoding='utf-8'));source=Path(old['source']);meta=path.with_name(path.name.replace('.analysis.json','.meta'))
        if not source.exists() or not meta.exists():
            skips.append({'analysis':str(path),'reason':'source or original Metadata absent'});continue
        if sha(source)!=old['source_sha256']:
            skips.append({'analysis':str(path),'reason':'source SHA differs from completed suite input'});continue
        if old['symbolic_encoding']!='expr_dag_v1' or old.get('metadata_schema',2)!=2 or old.get('provenance_inline',False) or not old.get('compact_bytecode',True):
            skips.append({'analysis':str(path),'reason':'earlier artifact used explicit nondefault settings'});continue
        assert sha(meta)==old['metadata_sha256']
        output=root/f'{i:03d}'/'default.meta'
        current=analyze(source,output,'C:/Program Files/LLVM/bin/clang.exe',old['function'])
        assert output.read_bytes()==meta.read_bytes()
        rows.append({'previous_analysis':str(path),'source':str(source),'function':old['function'],'source_sha256':sha(source),'old_metadata_sha256':sha(meta),'new_metadata_sha256':sha(output),'bytes':output.stat().st_size,'byte_identical':True})
        print(json.dumps({'index':i,'source':source.name,'bytes':output.stat().st_size,'identical':True}),flush=True)
    assert reports and rows and all(sha(project/name)==value for name,value in hashes.items())
    report={'passed':True,'discovered_accepted_analysis_artifacts':len(reports),'default_metadata_comparisons':len(rows),'skipped':skips,'rows':rows,'source_hashes':hashes,'wall_seconds':time.perf_counter()-started,'scope':'Every Clang-accepted default Metadata from the just-completed full schema2 suite, including programs later rejected for undefined integer execution; exact emitted Metadata bytes, no repeated C oracle/runtime work'}
    (root/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({'passed':True,'comparisons':len(rows),'skipped':len(skips),'wall_seconds':report['wall_seconds']}),flush=True)


if __name__=='__main__':main()
