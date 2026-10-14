"""Freeze R102 source/evidence without modifying older measured artifacts."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def manifest(folder):
    return {'isa_scheduler/' + path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.glob('*.py'))}


def main():
    current = manifest(ROOT / 'isa_scheduler')
    folder = ROOT / 'experiments/r102-phase-validation'
    destination = folder / 'source-provenance.json'
    snapshot = ROOT / 'experiments/baseline_phase_r102'
    if destination.exists() or snapshot.exists():
        raise ValueError('Already frozen; choose a new stage and preserve historical evidence')
    reports = ('r100-phases-336', 'r101-root-phase-heldout', 'r102-phase-10000')
    comparisons = {}
    for name in reports:
        report = json.loads((ROOT / 'experiments' / name / 'report.json').read_text(encoding='utf-8'))
        executed = {key.replace('\\', '/'): value
                    for key, value in report['current_source_manifest_at_start'].items()}
        different = sorted(key for key in set(current) | set(executed)
                           if current.get(key) != executed.get(key))
        if name == 'r100-phases-336':
            assert different in ([], ['isa_scheduler/__main__.py']), different
        else:
            assert not different, different
        comparisons[name] = {'different_current_source_paths': different,
                            'executed_core_aggregate_sha256': digest(executed)}
    snapshot.mkdir()
    for path in (ROOT / 'isa_scheduler').glob('*.py'):
        shutil.copy2(path, snapshot / path.name)
    assert manifest(snapshot) == current
    paths = [f'experiments/{name}/report.json' for name in reports]
    paths += [f'experiments/{name}/{filename}'
              for name in ('r100-phases-336', 'r101-root-phase-heldout')
              for filename in ('identity-replay.json', 'serialized-replay.json')]
    paths += ['experiments/r99-reduction-global-audit/report.json',
              'experiments/r102-phase-validation/tests.log']
    report = {
        'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'core_manifest': current,
        'core_aggregate_sha256': digest(current),
        'snapshot': str(snapshot.relative_to(ROOT)).replace('\\', '/'),
        'snapshot_usage': 'Import experiments.baseline_phase_r102.optimizer; explicit phase_portfolio. Default auto remains stage1 v14.',
        'frozen_r91_manifest': manifest(ROOT / 'experiments/baseline_level_r91'),
        'measured_source_comparisons': comparisons,
        'r100_difference_scope': '__main__.py CLI added explicit strategy choices during run; imported algorithm files unchanged. Do not claim every source file identical to its start manifest.',
        'evidence_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
        'tests': {'count': 149, 'elapsed_seconds': 49.798, 'path': 'tests.log'},
        'defaults': {'strategy': 'auto', 'time_budget_ms': 100, 'max_states': 30000, 'beam_width': 128, 'memory_order': 'hazard'},
        'validation_scope': 'New phase candidate: all original 336 inputs retained; 272 outputs plus 47 identity-model certificates, 9 budget and 8 heuristic failures. R101 60 valid, 3 model certificates, 1 budget. R102 9998 valid, 2 model certificates. No official Level claim.',
    }
    destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(destination), 'frozen_utc': report['frozen_utc'],
                      'core_aggregate_sha256': report['core_aggregate_sha256']}))


if __name__ == '__main__':
    main()
