"""Freeze official dependency and tested optional build without replacing release."""
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from finalize_runtime_release_stage2 import count_checks

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-metadata-zlib';build=project/'build-stage2-zlib'
    manifest=root/'manifest.json'
    if manifest.exists():raise SystemExit('Refusing to overwrite frozen zlib evidence')
    archive=root/'zlib-1.3.2.zip';archive_sha='e8bf55f3017aa181690990cb58a994e77885da140609fc8f94abe9b65d2cae28'
    assert sha(archive)==archive_sha;vendor_hashes={}
    with zipfile.ZipFile(archive) as zip:
        for info in zip.infolist():
            if info.is_dir():continue
            target=project/'third_party'/info.filename
            assert target.read_bytes()==zip.read(info),info.filename
            vendor_hashes[info.filename]=sha(target)
    dependency={'version':'1.3.2','source_url':'https://zlib.net/zlib132.zip','published_archive_sha256':archive_sha,'archive_sha256':sha(archive),'official_homepage':'https://zlib.net/','license_file':'third_party/zlib-1.3.2/LICENSE','license_sha256':sha(project/'third_party/zlib-1.3.2/LICENSE'),'unmodified_official_files':vendor_hashes,'static_library_sha256':sha(build/'third_party/zlib-1.3.2/libzs.a'),'existing_mingw_alternative':'1.3.1 libz.a exists but unused; official 1.3.2 source vendored for rebuild provenance'}
    (root/'dependency-provenance.json').write_text(json.dumps(dependency,indent=2),encoding='utf-8')
    shutil.copyfile(project/'third_party/zlib-1.3.2/LICENSE',root/'zlib-LICENSE')
    source_hashes={}
    names=['CMakeLists.txt','CMakePresets.json','README.md','docs/metadata.md','tools/analyze_source.py','tools/metadata_wire.py','tools/symbolic_metadata.py','tools/c_frontend.py','tools/semantic_cholesky.py','tools/evaluate_source.py','tools/metadata_container.py','tools/probe_metadata_zlib_stage2.py','tools/test_metadata_zlib_stage2.py','tools/finalize_metadata_zlib_stage2.py','tests/metadata_container_codec.cpp','include/cholesky/compressed_metadata.hpp','include/cholesky/runtime.hpp']
    names += [str(p.relative_to(project)).replace('\\','/') for p in sorted((project/'src').glob('*.cpp'))]
    for name in names:
        target=root/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,target);source_hashes[name]=sha(target)
    for name in ('cholesky_runtime.exe','metadata_container_codec.exe'):
        shutil.copyfile(build/name,root/name)
    for name in ('CMakeCache.txt','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/link.txt'):
        target=root/'build-source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(build/name,target)
    imports=subprocess.run(['E:/mingw64/bin/objdump.exe','-p',str(build/'cholesky_runtime.exe')],capture_output=True,text=True,check=True).stdout
    dlls=[line.split(':',1)[1].strip() for line in imports.splitlines() if 'DLL Name:' in line];assert not any('zlib' in item.lower() or item.lower()=='zlib1.dll' for item in dlls)
    flags=(build/'CMakeFiles/cholesky_core.dir/flags.make').read_text()
    assert '-fno-fast-math -ffp-contract=off' in flags and '-DCHOL_COMPRESSED_METADATA=1' in flags
    assert 'CHOL_PACKED_READY_KEYS:BOOL=OFF' in (build/'CMakeCache.txt').read_text()
    validation=json.loads((root/'validation/report.json').read_text());protocolpath=project/'artifacts/build-stage2-zlib-ctest-container/report.json';protocol=json.loads(protocolpath.read_text())
    assert validation['passed'] and validation['comparisons']==72 and protocol['passed'] and protocol['native_ieee754_bit_goldens']==12
    assert sha(build/'cholesky_runtime.exe')==validation['runtime_sha256']==protocol['runtime_sha256']==sha(root/'validation/runtime.exe')
    ordinary='4f73ceaae9e5b5ced6241d5733034d6fd7dc78fdae5c32bc3d7e65166e3d4c6c';assert sha(project/'build/cholesky_runtime.exe')==ordinary
    log=(root/'ctest.log').read_text();assert '100% tests passed, 0 tests failed out of 9' in log
    frozen=root/'ctest-evidence';frozen.mkdir()
    total=0;rejects=0
    for folder in sorted((project/'artifacts').glob('build-stage2-zlib-ctest-*')):
        shutil.copytree(folder,frozen/folder.name)
        if folder.name.endswith('pipeline'):file='test-report.json'
        elif folder.name.endswith('helpers'):file='helper-report.json'
        elif folder.name.endswith('while'):file='while-report.json'
        elif folder.name.endswith('integer-selectors'):file='integer-selector-report.json'
        else:continue
        report=json.loads((folder/file).read_text());assert report['passed']
        total+=count_checks(report);rejects+=len(report.get('rejection_cases',report.get('rejections',[])))
    assert total==405 and rejects==53
    assert source_hashes=={name:sha(project/name) for name in names}
    result={'status':'verified_optional_compressed_metadata','runtime_sha256':sha(build/'cholesky_runtime.exe'),'codec_sha256':sha(build/'metadata_container_codec.exe'),'unchanged_installed_ordinary_sha256':ordinary,'source_sha256':source_hashes,'dependency_provenance_sha256':sha(root/'dependency-provenance.json'),'ctest':9,'ctest_log_sha256':sha(root/'ctest.log'),'ctest_legacy_c_comparisons':405,'ctest_legacy_rejections':53,'wire_roundtrips':validation['roundtrips'],'original_c_comparisons':72,'container_rejections':len(protocol['container_rejections']),'inner_parser_rejections':len(protocol['inner_parser_rejections']),'ieee754_bit_goldens':12,'load_cost_metric':'metadata_read_ms includes reading, inflation and original text parser; separate from compute_ms','validation_report_sha256':sha(root/'validation/report.json'),'protocol_report_sha256':sha(protocolpath),'size_report_sha256':sha(root/'size-probe.json'),'runtime_dll_imports':dlls,'default_frontend_schema':2,'compressed_option_default':False,'packed_ready_keys':'OFF','auto_policy_unchanged':True,'smallest_interaction':'select minimum of six uncompressed encodings then compress its full bytes; no claim of global compressed minimum','limits':'16 MiB raw and compressed; uint32 little-endian; single RFC1950 stream; no dictionaries, trailing, concatenation, gzip/raw DEFLATE, nested parser schemas','limitations':'Local Metadata format and tests; no official score prediction; no kernel/compute speed claim; standard C++ MinGW runtime DLL prerequisites unchanged'}
    manifest.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'frozen':True,'runtime_sha256':result['runtime_sha256'],'ctest':9,'original_c_comparisons':72,'roundtrips':validation['roundtrips']}))

if __name__=='__main__':main()
