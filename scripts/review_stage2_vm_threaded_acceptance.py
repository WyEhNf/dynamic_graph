"""Verify immutable phase3 snapshots after later default sources are edited."""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/19-dynamic-graph'
FOLDER = PROJECT / 'artifacts/stage2-prepared-vm-phase3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    acceptance = json.loads((FOLDER / 'acceptance-manifest.json').read_text())
    final = json.loads((FOLDER / 'final-manifest.json').read_text())
    assert sha(FOLDER / 'acceptance-manifest.json') == final['acceptance_manifest_sha256']
    groups = [('source_sha256', 'candidate-source'), ('acceptance_sources_sha256', 'acceptance-source')]
    snapshots = 0
    for field, directory in groups:
        for filename, expected in acceptance[field].items():
            assert sha(FOLDER / directory / filename) == expected, filename
            snapshots += 1
    for filename, expected in final['final_evidence_sources_sha256'].items():
        assert sha(FOLDER / 'final-evidence-source' / filename) == expected, filename
        snapshots += 1
    evidence = {}
    for manifest, field in [(acceptance, 'evidence_sha256'), (final, 'final_evidence_sha256')]:
        for filename, expected in manifest[field].items():
            assert sha(FOLDER / filename) == expected, filename
            evidence[(FOLDER / filename).relative_to(ROOT).as_posix()] = expected
    log = (FOLDER / 'ctest.log').read_text()
    assert '100% tests passed, 0 tests failed out of 11' in log
    assert acceptance['actual_C_files'] == 378 and final['window_released']
    assert final['no_new_maximum_shape_test'] and not final['performance']['default_promotion']
    for filename in ('acceptance-manifest.json', 'final-manifest.json'):
        evidence[(FOLDER / filename).relative_to(ROOT).as_posix()] = sha(FOLDER / filename)
    result = dict(passed=True, reviewed_unix=time.time(), immutable_snapshot_files=snapshots,
                  ctest=11, actual_C_files=378, evidence=evidence,
                  scope='Immutable phase3 source/producers/complete C/performance/CTest manifests inspected after stage4 source edits. '
                        'Root separately reran934/404/480/GNU/portable/UBSan contracts and compared actual378 C files/130 measured C files. '
                        'Phase3 measured candidate remains isolated; stage4 default and N10000 require their own actual gates.')
    (ROOT / 'outputs/stage2-root-vm-threaded-acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
