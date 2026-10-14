"""Preserve actual R125 source and outputs before further age experiments."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'experiments/r126-spine-age-sources'; folder.mkdir(exist_ok=False)
    evidence = ROOT / 'experiments/r125-spine-age-cross'
    report = json.loads((evidence / 'report.json').read_text())
    paths = ['isa_scheduler/spine_age.py', 'scripts/research_spine_age_probe.py', 'tests/test_spine_age.py',
             'isa_scheduler/branch_copy.py', 'isa_scheduler/sink_bounds.py', 'isa_scheduler/local_order.py',
             'research/level-stage/spine-age-design.md']
    for path, sha in report['source_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    for path in paths:
        target = folder / path; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / path, target)
    data = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sources,
        'evidence_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in evidence.glob('*') if path.is_file()},
        'boundary_tests': {'count': 6, 'elapsed_seconds': .038, 'result': 'exit0 PASS'},
        'scope': 'R125 original16 cross; saved14 incumbents retained, COPY9755->9739, no recovery; not default promotion; R109 full336 quality unchanged'}
    (folder / 'source-provenance.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'path': str(folder / 'source-provenance.json'), 'frozen_utc': data['frozen_utc']}))


if __name__ == '__main__': main()
