"""Freeze the current ordinary Runtime and validated release provenance."""
import json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from benchmark_grain48_stage2 import sha


def count_checks(value):
    if isinstance(value,dict):return int(value.get('byte_identical') is True)+sum(count_checks(v) for v in value.values())
    if isinstance(value,list):return sum(count_checks(v) for v in value)
    return 0


def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-runtime-release';manifest=root/'release-manifest.json'
    if manifest.exists():raise SystemExit('Refusing to overwrite release manifest')
    history=json.loads((root/'historical-snapshots.json').read_text());runtime=project/'build/cholesky_runtime.exe'
    assert sha(root/'historical/row-runtime.exe')==history['snapshot_sha256']['row']
    assert sha(root/'historical/memory-runtime.exe')==history['snapshot_sha256']['memory']
    assert sha(project/'build-memory/cholesky_runtime.exe')==history['snapshot_sha256']['memory']
    cache=(project/'build/CMakeCache.txt').read_text();assert 'CHOL_PACKED_READY_KEYS:BOOL=OFF' in cache and 'CMAKE_BUILD_TYPE:STRING=Release' in cache
    geometry='workers>=8&&input.n>=4096?96u:64u';assert geometry in (project/'src/tiled_runtime.cpp').read_text()
    ctest=(root/'ctest.log').read_text();assert '100% tests passed, 0 tests failed out of 8' in ctest
    summaries=[]
    for label,filename in (('pipeline','test-report.json'),('helpers','helper-report.json'),('while','while-report.json'),('integer-selectors','integer-selector-report.json')):
        original=project/'artifacts'/f'build-release-stage2-metadata-ctest-{label}'/filename;record=json.loads(original.read_text())
        assert record['passed'];target=root/'ctest-evidence'/label/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
        rejections=record.get('rejection_cases',record.get('rejections',[]))
        summaries.append({'label':label,'frozen_report':str(target),'sha256':sha(target),'comparisons':count_checks(record),'rejections':len(rejections)})
    assert sum(x['comparisons'] for x in summaries)==405 and sum(x['rejections'] for x in summaries)==53
    wire=json.loads((root/'wire/report.json').read_text());minimum=json.loads((root/'smallest/report.json').read_text())
    assert wire['passed'] and wire['runtime_comparisons']==60 and minimum['passed'] and minimum['runtime_comparisons']==24
    assert wire['candidate_sha256']==minimum['runtime_sha256']==sha(runtime)
    assert json.loads((root/'quickstart-check.json').read_text())['byte_identical']
    source_paths=[project/'CMakeLists.txt',project/'CMakePresets.json',project/'README.md',*sorted((project/'src').glob('*.cpp')),*sorted((project/'include').rglob('*.hpp')),*sorted((project/'tests').glob('*.cpp')),
                  *[project/'tools'/name for name in ('analyze_source.py','metadata_wire.py','symbolic_metadata.py','c_frontend.py','semantic_cholesky.py','evaluate_source.py','test_metadata_wire_stage2.py','test_smallest_metadata_stage2.py','prepare_runtime_release_stage2.py','finalize_runtime_release_stage2.py')]]
    hashes={}
    for path in source_paths:
        target=root/'released-source'/path.relative_to(project);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);hashes[path.relative_to(project).as_posix()]=sha(target)
    shutil.copyfile(runtime,root/'runtime.exe')
    for name in ('CMakeCache.txt','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/link.txt'):
        target=root/'released-build'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/'build'/name,target)
    release={'status':'verified_current_ordinary_runtime','released_at_utc':datetime.now(timezone.utc).isoformat(),'installed_runtime':str(runtime),'runtime_sha256':sha(runtime),'frozen_runtime':str(root/'runtime.exe'),
             'source_sha256':hashes,'frontend_default_schema':2,'supported_runtime_schemas':[1,2,3],'smallest_metadata':'Explicit opt-in six equivalent candidate minimization; complete graph, bytecode and task dependencies retained',
             'build_type':'Release','packed_ready_keys':'OFF','unchanged_auto_geometry':geometry,'historical_snapshots':str(root/'historical-snapshots.json'),'historical_snapshot_sha256':sha(root/'historical-snapshots.json'),
             'ctest':{'passed':8,'seconds':110.40,'frozen_log':str(root/'ctest.log'),'sha256':sha(root/'ctest.log'),'rows':summaries,'original_c_comparisons':405,'rejections':53},
             'wire':{'report':str(root/'wire/report.json'),'sha256':sha(root/'wire/report.json'),'comparisons':60},'smallest':{'report':str(root/'smallest/report.json'),'sha256':sha(root/'smallest/report.json'),'comparisons':24},
             'quickstart':{'metadata':str(root/'quickstart-smallest.meta'),'metadata_sha256':sha(root/'quickstart-smallest.meta'),'original_c_check':str(root/'quickstart-check.json'),'sha256':sha(root/'quickstart-check.json')},
             'limitations':'Metadata bytes do not imply official 15 points. B128 remains explicit optional CLI geometry with measured 16-thread scope; AUTO not changed and no new performance attribution in this install.',
             'memory_runtime':'Original memory profile remains byte-exact 7da0; this release installs only ordinary build. Historical reports are unchanged.'}
    manifest.write_text(json.dumps(release,indent=2,ensure_ascii=False),encoding='utf-8')
    assert sha(runtime)==sha(root/'runtime.exe') and all(sha(project/name)==value for name,value in hashes.items())
    print(json.dumps({'released':True,'runtime_sha256':release['runtime_sha256'],'ctest':8,'original_c_comparisons':405,'rejections':53,'wire':60,'smallest':24,'manifest':str(manifest)}),flush=True)


if __name__=='__main__':main()
