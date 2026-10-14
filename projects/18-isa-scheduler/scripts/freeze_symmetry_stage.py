"""Freeze actual symmetry pairs separately from R119 baseline and quality."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / 'experiments/r122-symmetry-sources'; destination.mkdir(exist_ok=False)
    paths = ['isa_scheduler/retention_cpsat.py', 'isa_scheduler/matrix_symmetry.py',
             'scripts/research_cpsat_symmetry.py', 'tests/test_matrix_symmetry.py',
             'research/level-stage/matrix-symmetry-proof.md']
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    evidence = {}
    for stage in ('r120-cpsat-symmetry-holdout', 'r121-cpsat-symmetry-matrix'):
        folder = ROOT / 'experiments' / stage
        report = json.loads((folder / 'report.json').read_text())
        for path, value in report['source_sha256'].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value
        for path in folder.rglob('*'):
            if path.is_file(): evidence[str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in paths:
        target = destination / path; target.parent.mkdir(exist_ok=True, parents=True); shutil.copy2(ROOT / path, target)
    data = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sources,
            'evidence_sha256': evidence, 'default_optimizer_unchanged': True,
            'scope': 'Explicit pure resource row/column first-birth symmetry only; no new original336 outputs; R109 quality untouched'}
    (destination / 'source-provenance.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'path': str(destination / 'source-provenance.json'), 'frozen_utc': data['frozen_utc']}))


if __name__ == '__main__': main()
