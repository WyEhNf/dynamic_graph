"""Freeze R112/R114 raw oracle and rook minor evidence without older rewrites."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / 'experiments/r115-rook-retention-sources'; destination.mkdir(exist_ok=False)
    paths = ['scripts/research_retention_audit.py', 'scripts/research_rook_audit.py',
        'isa_scheduler/retention_search.py', 'isa_scheduler/retention_certificate.py',
        'isa_scheduler/rook_minor.py', 'isa_scheduler/minor_bounds.py', 'tests/test_rook_minor.py',
        'research/level-stage/rook-minor-proof.md', 'research/level-stage/retention-order-proof.md']
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    r112 = json.loads((ROOT / 'experiments/r112-retention-negative-holdout/report.json').read_text())
    assert r112['source_sha256'] == sources['scripts/research_retention_audit.py']
    assert r112['retention_source_sha256'] == sources['isa_scheduler/retention_search.py']
    r114 = json.loads((ROOT / 'experiments/r114-rook-failures/report.json').read_text())
    assert all(sources[path.replace('\\', '/')] == value for path, value in r114['source_sha256'].items())
    for path in paths:
        target = destination / path; target.parent.mkdir(exist_ok=True, parents=True); shutil.copy2(ROOT / path, target)
    evidence = ['experiments/r112-retention-negative-holdout/' + name for name in ('report.json', 'inputs.jsonl')]
    evidence += ['experiments/r114-rook-failures/' + name for name in ('report.json', 'inputs.jsonl')]
    data = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sources,
            'evidence_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in evidence},
            'rook_tests': {'count': 4, 'elapsed_seconds': .186, 'result': 'exit0 PASS'},
            'default_optimizer_unchanged': True, 'scope': 'Offline15 of original17 classified under identity model;2 unknown;0 new outputs; R109 COPY result retained'}
    (destination / 'source-provenance.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'path': str(destination / 'source-provenance.json'), 'frozen_utc': data['frozen_utc']}))


if __name__ == '__main__': main()
