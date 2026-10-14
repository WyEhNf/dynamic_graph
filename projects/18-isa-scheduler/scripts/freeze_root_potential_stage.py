"""Static file-I/O freeze of R127--R134 actual sources and complete evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(payload): return hashlib.sha256(payload).hexdigest()


def main():
    folder = ROOT / 'experiments/r135-root-potential-sources'; folder.mkdir(exist_ok=False)
    sources = ['isa_scheduler/spine_age.py', 'isa_scheduler/spine_macro.py', 'isa_scheduler/spine_potential.py',
               'isa_scheduler/root_potential_bound.py', 'isa_scheduler/branch_copy.py', 'isa_scheduler/sink_bounds.py',
               'isa_scheduler/local_order.py', 'scripts/research_spine_age_probe.py', 'scripts/research_spine_macro_probe.py',
               'scripts/research_spine_potential_probe.py', 'scripts/research_root_potential.py',
               'scripts/research_retention_audit.py', 'tests/test_spine_macro.py', 'tests/test_root_potential.py',
               'tests/test_spine_potential.py', 'research/level-stage/root-potential-proof.md',
               'research/level-stage/spine-macro-design.md']
    hashes = {}
    for path in sources:
        payload = (ROOT / path).read_bytes(); hashes[path] = sha(payload)
        target = folder / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(payload)
    # R129 ran before the explicit positive-spine option was added. Preserve
    # its exact original program, checking the actual hash recorded in R129.
    current = (ROOT / 'scripts/research_root_potential.py').read_text()
    original = current.replace("    parser.add_argument('--positive-spines', action='store_true')\n", '')
    start = original.index('    elif options.positive_spines:\n')
    end = original.index('    else:\n', start)
    original = original[:start] + original[end:]
    payload = original.replace('\r\n', '\n').encode()
    expected = json.loads((ROOT / 'experiments/r129-root-potential-oracle/report.json').read_text())['source_sha256']['scripts\\research_root_potential.py']
    assert sha(payload) == expected, 'R129 reconstruction is not the actual original source'
    old_path = 'versions/r129/scripts/research_root_potential.py'
    target = folder / old_path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(payload)
    hashes[old_path] = sha(payload)
    evidence = {}
    rounds = ['r127-spine-macro-cross', 'r128-spine-macro-heldout', 'r129-root-potential-oracle',
              'r130-root-potential-positive', 'r131-root-potential-cross', 'r132-spine-potential-cross',
              'r133-spine-potential-heldout', 'r134-root-potential-336']
    for name in rounds:
        report = json.loads((ROOT / 'experiments' / name / 'report.json').read_text())
        for source, expected_hash in report['source_sha256'].items():
            actual = (folder / old_path).read_bytes() if name == 'r129-root-potential-oracle' and source == 'scripts\\research_root_potential.py' else (ROOT / source).read_bytes()
            assert sha(actual) == expected_hash, (name, source)
        for path in (ROOT / 'experiments' / name).iterdir():
            if path.is_file(): evidence[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    manifest = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': hashes,
                'evidence_sha256': evidence,
                'tests': {'macro': '3 PASS .015s; first W4 positive assumption corrected to explicit restricted failure',
                          'root_potential': '3 PASS .003s including nonlatest raw COPY and tamper',
                          'conditional_rank': '2 PASS .053s'},
                'scope': 'Original336/72 quality/default unchanged. R127 no old16 gain; R128 new16 C1249->1129, R1331129->1124, 1unknown kept; necessary bounds separate from quality. Oracle409optimal/27infeasible/84unknown, positive-completed69.'}
    (folder / 'source-provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'path': str(folder / 'source-provenance.json'), 'frozen_utc': manifest['frozen_utc']}))


if __name__ == '__main__': main()
