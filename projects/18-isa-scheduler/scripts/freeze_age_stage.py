"""Freeze R109 candidate and evidence; never rewrite R102 or earlier snapshots."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def manifest(folder):
    return {'isa_scheduler/' + path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.glob('*.py'))}


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    current = manifest(ROOT / 'isa_scheduler')
    folder = ROOT / 'experiments/r109-age-validation'
    destination = folder / 'source-provenance.json'
    snapshot = ROOT / 'experiments/baseline_age_r109'
    if destination.exists() or snapshot.exists():
        raise ValueError('Already frozen; preserve artifacts and use another stage')
    comparisons = {}
    for name in ('r107-age-portfolio-336', 'r108-age-portfolio-heldout', 'r109-age-10000'):
        report = json.loads((ROOT / 'experiments' / name / 'report.json').read_text())
        executed = {key.replace('\\', '/'): value for key, value in report['current_source_manifest_at_start'].items()}
        different = sorted(key for key in set(current) | set(executed) if current.get(key) != executed.get(key))
        assert different in ([], ['isa_scheduler/__main__.py']), different
        if name == 'r109-age-10000':
            assert not different
        comparisons[name] = {'different_current_source_paths': different,
                            'executed_core_aggregate_sha256': digest(executed)}
    snapshot.mkdir()
    for path in (ROOT / 'isa_scheduler').glob('*.py'):
        shutil.copy2(path, snapshot / path.name)
    assert manifest(snapshot) == current
    paths = [f'experiments/{name}/report.json' for name in
        ('r103-age-dot', 'r104-age-cached-dot', 'r105-age-budget250', 'r106-age-structure-heldout',
         'r107-age-portfolio-336', 'r108-age-portfolio-heldout', 'r109-age-10000')]
    paths += [f'experiments/{name}/{artifact}' for name in
        ('r106-age-structure-heldout', 'r107-age-portfolio-336', 'r108-age-portfolio-heldout')
        for artifact in ('identity-replay.json', 'serialized-replay.json')]
    paths += ['experiments/r109-age-validation/tests.log']
    data = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'core_manifest': current,
        'core_aggregate_sha256': digest(current), 'snapshot': str(snapshot.relative_to(ROOT)).replace('\\', '/'),
        'frozen_phase_baseline_core_sha256': digest(manifest(ROOT / 'experiments/baseline_phase_r102')),
        'evidence_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
        'source_comparisons': comparisons,
        'source_difference_scope': 'Only __main__.py CLI explicit strategy choices added after R107/R108; algorithm files identical. R109 exact same core.',
        'tests': {'count': 153, 'elapsed_seconds': 45.037, 'path': 'tests.log'},
        'defaults': {'strategy': 'auto', 'time_budget_ms': 100, 'max_states': 30000, 'beam_width': 128, 'memory_order': 'hazard'},
        'candidate': {'strategy': 'age_portfolio', 'column_boundary_beam': 1, 'max_pending_products': 1,
                      'max_states_per_column': 4000, 'cache': 'local to a call; complete resource role state and first/last column flags'},
        'scope': 'Original336 retained:272 valid47 identity proof9 budget8 heuristic. New72:62 valid9 budget1 heuristic. Fuzz10000:9998 valid2 identity proof. No official Level claim.',
        'attribution': 'R107 total1590 fewer COPY includes1236 selected new reduction_age and354 legacy pressure budget-completion variation; never attribute354 to the new algorithm.',
    }
    destination.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'path': str(destination), 'core_sha256': digest(current), 'frozen_utc': data['frozen_utc']}))


if __name__ == '__main__':
    main()
