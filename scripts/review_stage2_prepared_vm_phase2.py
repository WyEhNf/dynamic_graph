"""Root reads every saved C oracle/native output and frozen predecoded VM source."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT/'projects/19-dynamic-graph'
DIRECTORY = PROJECT/'artifacts/stage2-prepared-vm-phase2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((DIRECTORY/'candidate-manifest.json').read_text())
    report = json.loads((DIRECTORY/'correctness/report.json').read_text())
    for name, expected in manifest['source_sha256'].items():
        assert sha(DIRECTORY/'candidate-source'/name) == expected, name
    for name, expected in manifest['proof_sha256'].items():
        assert sha(DIRECTORY/name) == expected, name
    assert sha(DIRECTORY/'candidate.exe') == manifest['candidate_sha256']
    assert sha(PROJECT/'build/cholesky_runtime.exe') == manifest['ordinary_sha256']
    assert sha(DIRECTORY/'native-contract.exe') == manifest['native_contract_exe_sha256']
    log = (DIRECTORY/'ctest.log').read_text()
    assert '100% tests passed, 0 tests failed out of 10' in log
    for source in report['sources']:
        base = DIRECTORY/'correctness'/source['label']
        for name, key in [('source.c','source_sha256'),('program.meta','metadata_sha256'),('oracle.exe','oracle_binary_sha256'),('oracle.c','harness_sha256')]:
            assert sha(base/name) == source[key]
    for row in report['runs']:
        base = DIRECTORY/'correctness'/row['source']
        actual = (base/f"{row['family']}-{row['backend']}.bin").read_bytes()
        expected = (base/f"{row['family']}-oracle.bin").read_bytes()
        assert actual == expected and len(actual) == row['bytes']
        assert hashlib.sha256(actual).hexdigest() == row['sha256'] == row['reference_sha256']
        assert sha(base/f"{row['family']}-input.bin") == row['input_sha256']
        assert row['selected_engine'] == 'vm'
    assert len(report['runs']) == 290 and len(report['sources']) == 12
    for row in report['failures']:
        outcomes = {(r['code'],r['stderr']) for r in row['results']}
        assert len(outcomes) == 1 and next(iter(outcomes))[0] != 0
    assert len(report['failures']) == 7
    run = subprocess.run([str(DIRECTORY/'native-contract.exe')],capture_output=True,text=True,check=True)
    native = json.loads(run.stdout)
    assert native['passed'] and native['comparisons'] == 480 and native['raw_stack_operations'] == 100000
    result = dict(reviewed_unix=time.time(),passed=True,actual_output_files=290,
                  source_files=len(manifest['source_sha256']),vm_required_sources=12,
                  preserved_error_contracts=7,root_rerun_native_contract=native,ctest=10,
                  candidate_exe_sha256=manifest['candidate_sha256'],
                  evidence={name:sha(DIRECTORY/name) for name in ('candidate-manifest.json','correctness/report.json','ctest.log')},
                  scope='Full actual C output bytes including headers, original input/source/harness/oracle/Metadata hashes and frozen candidate files checked. Frozen native-contract executable rerun by root;480 triple backend opcode/error/step comparisons and100000 payload operations pass. Optional TOS2 phase2 only, defaultOFF. No performance or universal correctness claim; explicitFMA and N10000 fallback-resource supplements pending.')
    (ROOT/'outputs/stage2-root-prepared-vm-phase2.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
