"""Freeze actual R116--R118 sources and raw models without prior rewrites."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / 'experiments/r119-cpsat-sources'; destination.mkdir(exist_ok=False)
    paths = ['isa_scheduler/retention_cpsat.py', 'isa_scheduler/local_order.py',
             'isa_scheduler/incremental.py', 'isa_scheduler/model.py',
             'scripts/research_cpsat_audit.py', 'scripts/research_cpsat_matrix.py',
             'tests/test_retention_cpsat.py', 'requirements-cpsat.lock', 'scripts/setup-cpsat.ps1',
             'research/level-stage/retention-cpsat-model.md']
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    evidence = {}
    for stage in ('r116-cpsat-oracle', 'r117-cpsat-negative', 'r118-cpsat-matrix'):
        folder = ROOT / 'experiments' / stage
        report = json.loads((folder / 'report.json').read_text())
        assert all(sources[path.replace('\\', '/')] == value for path, value in report['source_sha256'].items())
        for path in folder.rglob('*'):
            if path.is_file(): evidence[str(path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in paths:
        target = destination / path; target.parent.mkdir(exist_ok=True, parents=True); shutil.copy2(ROOT / path, target)
    data = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sources,
            'evidence_sha256': evidence, 'default_optimizer_unchanged': True,
            'scope': 'Optional CP-SAT exact feasibility model; 2240 comparisons zero contradictions; two matrix UNKNOWN; R109 quality untouched'}
    (destination / 'source-provenance.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'path': str(destination / 'source-provenance.json'), 'frozen_utc': data['frozen_utc']}))


if __name__ == '__main__': main()
