"""Preserve actual all-state producer and fixed-incumbent probe versions."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'experiments/r142-lifetime-sources'; folder.mkdir(exist_ok=False)
    sources = ['isa_scheduler/spine_lifetime.py', 'isa_scheduler/spine_age.py',
               'isa_scheduler/root_potential_bound.py', 'isa_scheduler/branch_copy.py',
               'isa_scheduler/sink_bounds.py', 'isa_scheduler/local_order.py',
               'scripts/research_lifetime_state_audit.py', 'scripts/research_lifetime_negative_audit.py',
               'scripts/research_spine_lifetime_probe.py', 'tests/test_spine_lifetime.py',
               'research/level-stage/lifetime-floor-proof.md']
    hashes = {}
    for path in sources:
        target = folder / path; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
        hashes[path] = hashlib.sha256(target.read_bytes()).hexdigest()
    evidence = {}
    for name in ['r136-lifetime-state-oracle', 'r137-lifetime-negative-state',
                 'r138-spine-lifetime-cross', 'r139-spine-lifetime-heldout',
                 'r140-spine-lifetime-macro-cross', 'r141-spine-lifetime-macro-heldout']:
        report = json.loads((ROOT / 'experiments' / name / 'report.json').read_text())
        for source, expected in report['source_sha256'].items():
            assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == expected, (name, source)
        for path in (ROOT / 'experiments' / name).iterdir():
            if path.is_file(): evidence[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': hashes,
                'evidence_sha256': evidence,
                'boundary_tests': {'count': 3, 'elapsed_seconds': .093, 'result': 'exit0 PASS',
                                   'first_failure': 'One expected error-message assertion: direct GET->SET rejected earlier by branch matcher; corrected wording, no core change'},
                'scope': '136 raw graphs: 124 complete feasible graphs, 12 closed infeasible, 72744 finite states including34514positive floor,1344dead-prefix; zero violations; unknown controls explicit. Old16/new16 same1000ms beam1/4, original best−3COPY/new pervariant−4, no recoveries/default promotion/full336 rerun.'}
    (folder / 'source-provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'path': str(folder / 'source-provenance.json'), 'frozen_utc': manifest['frozen_utc']}))


if __name__ == '__main__': main()
