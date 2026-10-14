"""Freeze the final-byte selector revision with prior immutable native evidence."""
import hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-compressed-smallest';manifest=root/'manifest.json'
    if manifest.exists():raise SystemExit('Refusing to replace selector evidence')
    priorpath=project/'artifacts/stage2-metadata-zlib/manifest.json';prior=json.loads(priorpath.read_text())
    reportpath=root/'report.json';report=json.loads(reportpath.read_text());assert report['passed'] and report['comparisons']==24
    assert report['prior_manifest_sha256']==sha(priorpath)
    assert report['runtime_sha256']==prior['runtime_sha256']==sha(root/'runtime.exe')
    assert report['codec_sha256']==prior['codec_sha256']==sha(root/'codec.exe')
    assert report['ordinary_runtime_sha256']==prior['unchanged_installed_ordinary_sha256']==sha(project/'build/cholesky_runtime.exe')
    assert sha(project/'build-memory/cholesky_runtime.exe')=='7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'
    for name,expected in prior['source_sha256'].items():
        if name.startswith('src/') or name in ('CMakeLists.txt','include/cholesky/compressed_metadata.hpp','tests/metadata_container_codec.cpp'):
            assert sha(project/name)==expected,name
    # The production selector and imported semantic compiler match tested snapshots.
    for name in ('tools/analyze_source.py','tools/metadata_container.py','tools/metadata_wire.py','tools/symbolic_metadata.py','tools/c_frontend.py','tools/semantic_cholesky.py','tools/evaluate_source.py','tools/test_compressed_smallest_stage2.py'):
        assert sha(project/name)==report['source_sha256'][name],name
    current={}
    for name in ('README.md','docs/metadata.md','tools/analyze_source.py','tools/metadata_container.py','tools/test_metadata_zlib_stage2.py','tools/test_compressed_smallest_stage2.py','tools/finalize_compressed_smallest_stage2.py'):
        target=root/'current-source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,target);current[name]=sha(target)
    selections=[]
    for source in report['sources']:
        assert source['compilation_counts']=={'ast':1,'llvm_ir':1} and len(source['candidates'])==6
        assert source['uncompressed_default_and_minimum_unchanged'] and source['explicit_single_format_preserved']
        candidate=source['selection'];expected=min(source['candidates'],key=lambda row:(row['metadata_bytes'],row['metadata_schema'],('dag','table','expanded').index(row['symbolic_format'])))
        assert all(candidate[key]==expected[key]for key in candidate)
        selections.append({'source':source['source'],'source_sha256':source['source_sha256'],'old_bytes':source['prior_compressed_minimum_bytes'],**candidate})
    result={'status':'verified_final_container_byte_minimum','frozen_at_utc':datetime.now(timezone.utc).isoformat(),'prior_immutable_manifest':str(priorpath),'prior_manifest_sha256':sha(priorpath),'prior_compression_mode':'minimum UTF8 candidate then compression; frozen report preserved','current_compression_mode':'minimum of six complete final containers if both flags enabled; unchanged UTF8 metric otherwise','prior_native_regression':{'passed':9,'sha256':prior['ctest_log_sha256'],'runtime_sha256':prior['runtime_sha256'],'note':'No native/kernel/build changes in this selector revision; 9/9 is earlier identical binary evidence'},'runtime_sha256':report['runtime_sha256'],'ordinary_runtime_sha256':report['ordinary_runtime_sha256'],'tested_source_sha256':report['source_sha256'],'current_document_and_support_source_sha256':current,'report_sha256':sha(reportpath),'related_frontend_regression':{'original_c_full_file_comparisons':24,'fully_expanded_equivalent_candidates':36,'uncompressed_default_cases':6,'uncompressed_minimum_cases':6,'explicit_compressed_format_cases':6,'single_ast_and_ir_each_source':True,'cli_combination':True,'conflicting_cli_rejections':3,'seconds':report['wall_seconds']},'tie_rule':report['tie_rule'],'all_candidate_sizes_and_sha':'report.json retains all six raw and final sizes/hashes per source including larger/equal choices','selections':selections,'default_frontend_schema':2,'compressed_container_opt_in':True,'ordinary_runtime_replaced':False,'limitations':'No new performance attribution, no official 15-point prediction; minimum only within the six legal complete encodings under the frozen zlib encoder version'}
    manifest.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'frozen':True,'comparisons':24,'sizes':[row['metadata_bytes']for row in selections],'manifest':str(manifest)}))

if __name__=='__main__':main()
