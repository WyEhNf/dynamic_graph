"""Root check of actual C-output files, frozen sources and all paired costs."""
import hashlib
import json
import re
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/19-dynamic-graph'
DIR = PROJECT / 'artifacts/stage2-avx512'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    final, manifest, snapshot = (read(DIR / name) for name in ('final-manifest.json', 'candidate-manifest.json', 'candidate-source/snapshot-manifest.json'))
    assert sha(DIR/'candidate-manifest.json') == final['candidate_manifest_sha256']
    assert sha(DIR/'final-manifest.json') == snapshot['parent_final_manifest_sha256']
    for relative, expected in snapshot['files'].items():
        assert sha(DIR/'candidate-source'/relative) == expected
    for relative, expected in final['source_sha256'].items():
        assert snapshot['files'][relative] == expected
    assert sha(DIR/'candidate/runtime.exe') == final['candidate_runtime_sha256']
    assert sha(PROJECT/'build/cholesky_runtime.exe') == final['ordinary_sha256']
    assert sha(PROJECT/'build-memory/cholesky_runtime.exe') == final['memory_sha256']
    correct = read(DIR/'correctness/report.json')
    assert sha(DIR/'correctness/report.json') == manifest['functional_report_sha256']
    assert len(correct['runs']) == 240 and correct['passed']
    for source in correct['sources']:
        folder = DIR/'correctness'/source['label']
        for file, field in [('source.c','source_sha256'),('program.meta','metadata_sha256'),('oracle.exe','oracle_sha256'),('oracle.c','harness_sha256')]:
            assert sha(folder/file) == source[field]
    for row in correct['runs']:
        folder = DIR/'correctness'/row['source']
        output = folder/f"{row['family']}-{row['mode']}-B{row['tile_size']}-t{row['worker_threads']}.bin"
        oracle = folder/f"{row['family']}-oracle.bin"
        actual = output.read_bytes()
        assert actual == oracle.read_bytes()
        assert len(actual) == row['bytes'] and hashlib.sha256(actual).hexdigest() == row['sha256'] == row['oracle_output_sha256']
    native = read(DIR/'native-kernel-tests-final.json')
    assert native == dict(passed=True,gate_rejections=11,ieee754_goldens=16,guard_page_cases=1400)
    assert sha(DIR/'native-kernel-tests-final.json') == manifest['native_final_sha256']
    assert sha(DIR/'ctest.log') == manifest['ctest_log_sha256']
    assert '100% tests passed, 0 tests failed out of 9' in (DIR/'ctest.log').read_text()
    for name in ('binary-entry.asm','binary-detector.asm'):
        text = (DIR/name).read_text()
        assert not re.search(r'%[zy]mm\d+',text) and not re.search(r'^\s*[0-9a-f]+:\s+62\s',text,re.M)
    plan, perf = read(DIR/'performance/run-plan-v2.json'), read(DIR/'performance/performance.json')
    assert sha(DIR/'performance/run-plan-v2.json') == perf['plan_sha256'] == final['plan_v2_sha256']
    assert sha(DIR/'performance/performance.json') == final['performance_sha256']
    assert perf['passed'] and perf['status'] == 'complete' and len(perf['records']) == 60
    references = {r['n']:r for r in plan['references']}
    for reference in references.values():
        assert sha(Path(reference['input'])) == reference['input_sha256']
        assert sha(Path(reference['oracle'])) == reference['oracle_sha256']
    records = {(r['n'],r['tile'],r['repeat'],r['simd']):r for r in perf['records']}
    assert len(records) == 60
    summaries = []
    for n in (6145,8193,10000):
        for tile in (96,128):
            ratios, before, after = [], [], []
            for repeat in range(5):
                pair = [records[n,tile,repeat,mode] for mode in ('avx2','avx512')]
                for r in pair:
                    assert r['byte_identical'] and r['sha256'] == references[n]['oracle_sha256']
                    assert r['threads'] == r['worker_threads'] == 16 and r['effective_tile_size'] == tile
                    assert r['verified_before_trial_sha256'] == dict(input=references[n]['input_sha256'],original_c_output=references[n]['oracle_sha256'],original_c_source=references[n]['source_sha256'],metadata=plan['metadata_sha256'],runtime=plan['runtime_sha256'])
                before.append(pair[0]['compute_ms']);after.append(pair[1]['compute_ms']);ratios.append(after[-1]/before[-1])
            saved = next(s for s in final['results'] if s['n']==n and s['tile']==tile)
            assert ratios == saved['paired_ratios']
            assert statistics.median(before) == saved['avx2_compute_ms']['median']
            assert statistics.median(after) == saved['avx512_compute_ms']['median']
            summaries.append(dict(n=n,tile=tile,ratio_of_medians=statistics.median(after)/statistics.median(before),median_paired_ratio=statistics.median(ratios),losses=sum(r>1 for r in ratios),paired_ratios=ratios))
    assert sum(s['losses'] for s in summaries) == 11
    result = dict(reviewed_unix=time.time(),passed=True,actual_small_output_files=240,
                  snapshot_files=len(snapshot['files']),performance_records=60,negative_pairs=11,
                  summaries=summaries,native=native,
                  evidence={name:sha(DIR/name) for name in ('final-manifest.json','candidate-manifest.json','candidate-source/snapshot-manifest.json','correctness/report.json','performance/run-plan-v2.json','performance/performance.json')},
                  scope='Root reads all240 saved native outputs and actual C reference files including headers; compares full bytes, verifies frozen source/executable evidence, recorded feature gates and CTest terminal log, and independently recomputes every60-trial paired statistic. Large dense original C input/output files independently hashed once; every trial recorded exact hashes and byte comparisons inspected, no repeat execution claimed.',
                  interpretation='Optional candidate only:6145/B128 median22.75 percent slower,11/30 pairs regress,10000 median gains below1 percent and one50.73 percent tail regression. Default4f73/AUTO unchanged; no official or universal performance claim.')
    (ROOT/'outputs/stage2-root-avx512-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,actual_outputs=240,performance_records=60,negative_pairs=11)))


if __name__ == '__main__':
    main()
