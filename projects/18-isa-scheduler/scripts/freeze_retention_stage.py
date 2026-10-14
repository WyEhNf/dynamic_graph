"""Preserve the R110/111 experimental feasibility stage before new generators."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'experiments/r113-retention-stage'; folder.mkdir(exist_ok=True)
    target = folder / 'source-provenance.json'; snapshot = folder / 'isa_scheduler'
    if target.exists() or snapshot.exists(): raise ValueError('Already frozen; preserve history')
    manifest = {'isa_scheduler/' + path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted((ROOT / 'isa_scheduler').glob('*.py'))}
    r110 = json.loads((ROOT / 'experiments/r110-retention-failures/report.json').read_text())
    executed = {key.replace('\\', '/'): value for key, value in r110['current_source_manifest_at_start'].items()}
    assert executed == manifest
    r111 = json.loads((ROOT / 'experiments/r111-retention-oracle/report.json').read_text())
    assert r111['retention_source_sha256'] == manifest['isa_scheduler/retention_search.py']
    assert r111['source_sha256'] == hashlib.sha256((ROOT / 'scripts/research_retention_audit.py').read_bytes()).hexdigest()
    snapshot.mkdir()
    for path in (ROOT / 'isa_scheduler').glob('*.py'): shutil.copy2(path, snapshot / path.name)
    source_paths = ['scripts/research_retention_audit.py', 'scripts/research_retention_probe.py',
                    'scripts/research_benchmark.py', 'tests/test_retention_search.py',
                    'research/level-stage/retention-order-proof.md']
    for name in ('research_retention_audit.py', 'research_retention_probe.py', 'research_benchmark.py'):
        shutil.copy2(ROOT / 'scripts' / name, folder / name)
    evidence = ['experiments/r110-retention-failures/' + name for name in
        ('report.json', 'inputs.jsonl', 'retention-proofs.jsonl', 'retention-entry-provenance.json')]
    evidence += ['experiments/r111-retention-oracle/' + name for name in ('report.json', 'inputs.jsonl')]
    evidence += ['experiments/r113-retention-stage/boundary-tests.log']
    aggregate = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    result = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'core_manifest': manifest,
        'core_aggregate_sha256': aggregate, 'source_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in source_paths},
        'evidence_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in evidence},
        'baseline_r109_sha256': '0c3d19724d85e33ce7bc8cfba24feb94c0bb3a0b3770091be50fd8aaa4b28af4',
        'scope': 'Standalone retention probe only. Default auto and age_portfolio unchanged. '
                 'R110 original17:0 outputs,9 independently replayed closed-mask certificates,8 matrix budget unknown. '
                 'R111:1992 jointly complete consistent;30 negative fixed-order;8 raw unknown/new constructive. '
                 'Not COPY optimization or an official Level verdict.'}
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'path': str(target), 'core_sha256': aggregate, 'frozen_utc': result['frozen_utc']}))


if __name__ == '__main__': main()
