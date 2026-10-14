"""Independent root checks of frozen stage2 artifacts, without rebuilding them."""
import hashlib
import json
import re
import struct
import time
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P19 = ROOT / 'projects/19-dynamic-graph'
P27 = ROOT / 'projects/27-aicore-streams'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


zdir = P19 / 'artifacts/stage2-metadata-zlib'
manifest = read(zdir / 'manifest.json')
assert manifest['status'] == 'verified_optional_compressed_metadata'
assert sha(zdir / 'cholesky_runtime.exe') == manifest['runtime_sha256']
assert sha(P19 / 'build/cholesky_runtime.exe') == manifest['unchanged_installed_ordinary_sha256']
assert sha(zdir / 'metadata_container_codec.exe') == manifest['codec_sha256']
provenance = read(zdir / 'dependency-provenance.json')
archive = zdir / 'zlib-1.3.2.zip'
assert sha(archive) == provenance['archive_sha256'] == provenance['published_archive_sha256']
assert sha(P19 / provenance['license_file']) == provenance['license_sha256']
vendor_checked = 0
with zipfile.ZipFile(archive) as package:
    for relative, expected in provenance['unmodified_official_files'].items():
        assert hashlib.sha256(package.read(relative)).hexdigest() == expected
        assert sha(P19 / 'third_party' / relative) == expected
        vendor_checked += 1
validation = read(zdir / 'validation/report.json')
assert sha(zdir / 'validation/report.json') == manifest['validation_report_sha256']
assert validation['passed'] and validation['comparisons'] == len(validation['runs']) == 72
assert all(r['byte_identical'] for r in validation['runs'])
protocol = read(zdir / 'ctest-evidence/build-stage2-zlib-ctest-container/report.json')
assert sha(zdir / 'ctest-evidence/build-stage2-zlib-ctest-container/report.json') == manifest['protocol_report_sha256']
assert protocol['passed'] and protocol['roundtrips'] == 42
native_checked = []
for row in validation['files']:
    raw_path = Path(row['file'])
    raw = raw_path.read_bytes()
    assert sha(raw_path) == row['raw_sha256'] and len(raw) == row['raw_bytes']
    native_path = zdir / 'validation' / f"{row['source']}-{raw_path.stem}-encode.output"
    native = native_path.read_bytes()
    assert len(native) == row['container_bytes'] and sha(native_path) == row['container_sha256']
    assert native[:8] == b'DYNCHZ01'
    length, payload_length = struct.unpack('<II', native[8:16])
    assert length == len(raw) and payload_length == len(native) - 16
    inflater = zlib.decompressobj(wbits=15)
    decoded = inflater.decompress(native[16:], length + 1) + inflater.flush()
    assert inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail
    assert decoded == raw
    native_checked.append(dict(source=row['source'], file=raw_path.name, raw=len(raw), container=len(native)))
assert len(native_checked) == 42
size = read(zdir / 'size-probe.json')
assert sha(zdir / 'size-probe.json') == manifest['size_report_sha256']
assert len(size['rows']) == 57
for row in size['rows']:
    path = Path(row['path'])
    raw = path.read_bytes()
    assert sha(path) == row['sha256'] and len(raw) == row['bytes']
    stream = zlib.compress(raw, level=size['level'])
    assert len(stream) == row['zlib_stream_bytes']
    assert 16 + len(stream) == row['container_bytes']
    assert zlib.decompress(stream) == raw
choice = []
for source in ('scalar', 'page', 'blocked', 'generic', 'negative-zero', 'noop'):
    rows = [r for r in size['rows'] if Path(r['path']).parent.name == source and
            re.fullmatch('[23]-(dag|table|expanded)\\.meta', Path(r['path']).name)]
    assert len(rows) == 6
    raw_min = min(rows, key=lambda r: r['bytes'])
    final_min = min(rows, key=lambda r: r['container_bytes'])
    choice.append(dict(source=source, current_container=raw_min['container_bytes'],
                       minimum_six_containers=final_min['container_bytes'],
                       minimum_format=Path(final_min['path']).stem,
                       all_candidate_sizes={Path(r['path']).stem:r['container_bytes'] for r in rows}))

final27 = read(P27 / 'reports/final-checkpoint-batch42.json')
assert final27['status'] == 'validated_correctness_default_milestone'
assert sha(P27 / 'solution/solution.cpp') == final27['source_sha256']
assert sha(P27 / 'src/simulator.cpp') == final27['independent_simulator_sha256']
assert sha(P27 / 'build/aicore_bench.exe') == final27['default_exe_sha256']
assert sha(P27 / 'research/batch42/default-aicore_bench.exe') == final27['default_exe_sha256']
direct = read(P27 / 'reports/direct-normal-r39-batch42.json')
assert direct['all_same'] and direct['records'] == 979
normal_checked = 0
for suite in direct['suites']:
    reports = []
    for direction in ('before', 'after'):
        path = P27 / suite[f'{direction}_report']
        assert sha(path) == suite[f'{direction}_report_sha256']
        data = read(path)
        cases = {c['name']: c for c in data['cases']}
        assert len(cases) == suite['records']
        reports.append(cases)
    before, after = reports
    assert before.keys() == after.keys()
    for name in before:
        assert all(before[name][key] == after[name][key] for key in ('pass','T','peak_memory'))
    normal_checked += len(before)
assert normal_checked == 979
result = dict(reviewed_unix=time.time(),passed=True,
              project19=dict(official_vendor_archive_files_checked=vendor_checked,
                             full_native_containers_decoded_by_python=42,
                             frozen_full_metadata_sizes_recomputed=57,
                             original_c_whole_file_results=72,
                             new_compressed_choice_opportunity=choice,
                             runtime_sha256=manifest['runtime_sha256']),
              project27=dict(direct_frozen_r39_to_r42_normal_records=979,
                             fields=['pass','T','peak_memory'],all_same=True,
                             default_binary_sha256=final27['default_exe_sha256'],
                             limitation='Numerical correction does not recover the63 known feasible unresolved cases or establish universal solver correctness.'),
              evidence={str(p.relative_to(ROOT)):sha(p) for p in
                        [zdir/'manifest.json',zdir/'validation/report.json',zdir/'size-probe.json',
                         P27/'reports/final-checkpoint-batch42.json',P27/'reports/direct-normal-r39-batch42.json']})
destination = ROOT / 'outputs/stage2-root-release-review.json'
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True, vendor_files=vendor_checked, full_native_containers=42,
                      direct_normal_records=979, compressed_choice_opportunities=choice),ensure_ascii=False))
