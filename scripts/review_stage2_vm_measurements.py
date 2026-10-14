"""Root streaming verification of maximum shape and all90 predecoded VM pairs."""
import hashlib
import json
import statistics
import struct
import time
from contextlib import ExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase1'


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
    maximum = STAGE/'maximum-shape'
    m = json.loads((maximum/'report.json').read_text())
    assert m['passed'] and m['status']=='complete' and m['plan']['sizes']==[10000]
    rows = m['runs']
    assert len(rows)==4 and m['plan']['budget']==10000000000
    paths = [maximum/'input.bin',maximum/'oracle.bin']+[maximum/(r['backend']+'.bin') for r in rows]
    size,digests = compare_files(paths)
    assert size==800000008 and digests[0]==m['input_sha256'] and digests[1]==m['oracle_output_sha256']
    with paths[0].open('rb') as source:
        assert source.read(8)==struct.pack('<II',1,10000)
    for row,digest in zip(rows,digests[2:]):
        assert row['sha256']==digest and row['bytes']==size and row['selected_engine']=='vm'
        assert row['free_memory_before_kib']>=2621440 and row['resource_samples']>0
    assert len({r['vm_steps'] for r in rows if 'vm_steps' in r})==1
    assert rows[1]['vm_steps']==1700000012
    perf = STAGE/'performance-v3'
    p = json.loads((perf/'run-plan.json').read_text())
    report = json.loads((perf/'report.json').read_text())
    assert p['version']==3 and report['passed'] and report['status']=='complete'
    assert sha(perf/'run-plan.json')==report['plan_sha256']
    assert sha(perf/'runtime.exe')==p['runtime_sha256']
    assert sha(perf/'benchmark-script.py')==p['script_sha256']
    assert sha(perf/'windows_resource_probe.py')==p['resource_probe_sha256']
    records = {(r['source'],r['round'],r['backend']):r for r in report['records']}
    assert len(records)==90
    summaries = []
    for case in p['cases']:
        folder = perf/case['source']
        for name,expected in case['hashes'].items():
            assert sha(folder/name)==expected
        cached = STAGE/'correctness'/case['source']
        for name,target in [('dense-input.bin','input.bin'),('dense-oracle.bin','oracle.bin')]:
            check_repeat(cached/name,folder/target,case['whole_stream_repeats'])
        ratios = []
        for repeat in range(5):
            pair = [records[case['source'],repeat,backend] for backend in ('legacy','decoded')]
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
        assert sum(x<1 for x in ratios)==summary['decoded_compute_wins']
        summaries.append(dict(source=case['source'],median_paired_ratio=statistics.median(ratios),negative_pairs=sum(x>1 for x in ratios)))
    assert len(summaries)==9 and sum(s['negative_pairs'] for s in summaries)==2
    result = dict(reviewed_unix=time.time(),passed=True,maximum_shape=10000,
                  full_maximum_outputs=4,bytes_per_maximum_output=800000008,
                  maximum_vm_steps=1700000012,explicit_maximum_step_limit=10000000000,
                  max_peak_working_set=max(r['process_peak_working_set_bytes'] for r in rows),
                  performance_records=90,paired_comparisons=45,negative_pairs=2,summaries=summaries,
                  host_busy_percent_range=[min(r['host_busy_percent_during_process'] for r in records.values()),max(r['host_busy_percent_during_process'] for r in records.values())],
                  evidence={path.relative_to(ROOT).as_posix():sha(path) for path in (maximum/'report.json',maximum/'plan.json',perf/'report.json',perf/'run-plan.json')},
                  scope='Root streaming comparison of all4 full N10000 outputs against input identity semantics and actualC; bounded buffers. All90 wholeC output comparisons and45 paired ratios recomputed, cached originalC stream repeats verified. Compute includes decoding. N10000 VM copy fixture needs explicit1e10 steps; default1e9 does not support its1.7b steps. Backgroundhost CPU26–53percent active, so evidence is local paired performance under that recorded load, not idle-machine or universal speed. Candidate remains optional.')
    (ROOT/'outputs/stage2-root-vm-measurements.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
