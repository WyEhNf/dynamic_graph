"""Root full-file C comparisons plus independent exact IEEE constant goldens."""
import hashlib
import json
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase1/fp-supplement'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = json.loads((DIRECTORY/'report.json').read_text())
    assert report['passed'] and report['status']=='complete'
    for name,key in [('source.c','source_sha256'),('program.meta','metadata_sha256'),('oracle.exe','oracle_binary_sha256'),('oracle.c','oracle_harness_sha256'),('input.bin','input_sha256')]:
        assert sha(DIRECTORY/name)==report[key]
    reference = (DIRECTORY/'oracle.bin').read_bytes()
    assert hashlib.sha256(reference).hexdigest()==report['oracle_output_sha256']
    for row in report['runs']:
        actual = (DIRECTORY/(row['backend']+'.bin')).read_bytes()
        assert actual==reference and len(actual)==row['bytes']==167412
        assert hashlib.sha256(actual).hexdigest()==row['sha256']
        assert row['selected_engine']=='vm'
    assert len(report['runs'])==4
    # (1+2^-27)*(1-2^-27)-1=-2^-54 exactly when explicitly fused;
    # strict rounded multiply gives1 and subsequent subtraction gives +0.
    expected = {0:0xbc90000000000000,1:0,3:0x0008000000000000,5:0x4000000000000000}
    cursor = 4
    assert struct.unpack_from('<I',reference)[0]==4
    checked = 0
    for n in (3,7,65,129):
        assert struct.unpack_from('<I',reference,cursor)[0]==n;cursor+=4
        for i in range(n*n):
            if i%8 in expected:
                assert struct.unpack_from('<Q',reference,cursor+8*i)[0]==expected[i%8]
                checked+=1
        cursor+=8*n*n
    assert cursor==len(reference)
    result = dict(reviewed_unix=time.time(),passed=True,full_file_C_outputs=4,
                  independent_constant_bit_checks=checked,bytes_per_output=167412,
                  evidence={p.relative_to(ROOT).as_posix():sha(p) for p in (DIRECTORY/'report.json',DIRECTORY/'source.c',DIRECTORY/'program.meta',DIRECTORY/'oracle.bin')},
                  scope='Root actual wholeC bytes including headers match all4 backends. Explicit fused -2^-54, unfused +0, subnormal half-minimum-normal and exactsqrt4 constants independently checked at every selected matrix element. FP sequence preservation verified on these fixtures; no performance/universal claim.')
    (ROOT/'outputs/stage2-root-vm-fp.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
