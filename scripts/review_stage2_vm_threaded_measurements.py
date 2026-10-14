"""Root streaming verification of maximum shape and all90 predecoded VM pairs."""
import hashlib
import json
import statistics
import struct
import time
from contextlib import ExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase3'


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1048576),b''):
            value.update(chunk)
    return value.hexdigest()


def compare_files(paths):
    hashes = [hashlib.sha256() for _ in paths]
    size = 0
    with ExitStack() as stack:
        streams = [stack.enter_context(path.open('rb')) for path in paths]
        while True:
            blocks = [stream.read(1048576) for stream in streams]
            assert all(block==blocks[0] for block in blocks)
            if not blocks[0]:
                break
            size+=len(blocks[0])
            for value,block in zip(hashes,blocks):
                value.update(block)
    return size,[value.hexdigest() for value in hashes]


def check_repeat(original,repeated,repeats):
    # The cached originalC body includes every per-matrix N header.
    old = original.read_bytes()
    count = struct.unpack_from('<I',old)[0]
    with repeated.open('rb') as source:
        assert source.read(4)==struct.pack('<I',count*repeats)
        for _ in range(repeats):
            assert source.read(len(old)-4)==old[4:]
        assert not source.read(1)


def main():
    perf = STAGE/'performance'
    p = json.loads((perf/'run-plan.json').read_text())
    report = json.loads((perf/'report.json').read_text())
    assert p['version']==1 and report['passed'] and report['status']=='complete'
    assert sha(perf/'run-plan.json')==report['plan_sha256']
    assert sha(perf/'runtime.exe')==p['runtime_sha256']
    assert sha(perf/'benchmark-script.py')==p['script_sha256']
    assert sha(perf/'windows_resource_probe.py')==p['resource_probe_sha256']
    records = {(r['source'],r['round'],r['backend']):r for r in report['records']}
    assert len(records)==130
    summaries = []
    for case in p['cases']:
        folder = perf/case['source']
        for name,expected in case['hashes'].items():
            assert sha(folder/name)==expected
        functional=json.loads((STAGE/'correctness/report.json').read_text(encoding='utf-8'))
        original=next(row for row in functional['runs'] if row['source']==case['source'] and row['family']=='dense')
        check_repeat(Path(original['input']),folder/'input.bin',case['whole_stream_repeats'])
        check_repeat(Path(original['reference']),folder/'oracle.bin',case['whole_stream_repeats'])
        ratios = []
        for repeat in range(5):
            pair = [records[case['source'],repeat,backend] for backend in ('decoded','decoded-threaded')]
            for row in pair:
                size,hashes = compare_files([folder/'oracle.bin',folder/f"round-{repeat}-{row['backend']}.bin"])
                assert size==row['bytes'] and hashes[0]==hashes[1]==row['sha256']==row['reference_sha256']
                assert row['input_sha256']==case['hashes']['input.bin'] and row['source_sha256']==case['hashes']['source.c']
                assert row['vm_steps']==case['original_steps'] and row['selected_engine']=='vm' and row['vm_backend']==row['backend']
                assert row['resource_samples']>0 and 0<=row['host_busy_percent_during_process']<=100
                assert 0<=row['vm_prepare_ms']<=row['compute_ms']
            ratios.append(pair[1]['compute_ms']/pair[0]['compute_ms'])
        summary = next(r for r in report['summary'] if r['source']==case['source'])
        assert ratios==summary['paired_compute_ratios']
        assert statistics.median(ratios)==summary['median_paired_ratio']
        assert sum(x<1 for x in ratios)==summary['threaded_compute_wins']
        summaries.append(dict(source=case['source'],median_paired_ratio=statistics.median(ratios),negative_pairs=sum(x>1 for x in ratios)))
    assert len(summaries)==13 and sum(s['negative_pairs'] for s in summaries)==0
    result = dict(reviewed_unix=time.time(),passed=True,performance_records=130,
                  paired_comparisons=65,negative_pairs=0,summaries=summaries,
                  host_busy_percent_range=[min(r['host_busy_percent_during_process'] for r in records.values()),max(r['host_busy_percent_during_process'] for r in records.values())],
                  evidence={path.relative_to(ROOT).as_posix():sha(path) for path in (perf/'report.json',perf/'run-plan.json')},
                  scope='Root streaming comparison of all130 whole actualC output files and65 recomputed sameEXE decoded/threaded ratios, cached originalC input/output stream repeats and original source/Metadata/oracle/harness SHA verified. All65 threaded pairs faster, candidate remains isolated pending default/resource integration review. Decode included in compute; backgroundhost activity recorded, no idle or universal result. No threaded N10000 acceptance claim.')
    (ROOT/'outputs/stage2-root-vm-threaded-measurements.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
