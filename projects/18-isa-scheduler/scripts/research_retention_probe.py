"""Four-check paired harness for the explicit retention-order candidate."""
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import research_benchmark
from experiments.baseline_age_r109.optimizer import optimize as age_r109_optimize
from isa_scheduler.model import parse_block
from isa_scheduler.retention_search import schedule_retention
from isa_scheduler.retention_certificate import check_retention_certificate
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.model import InfeasibleSchedule

PROOFS = []


def run_retention(data, strategy, time_budget_ms=250, max_states=30000, **kwargs):
    try:
        return schedule_retention(parse_block(data), time_budget_ms=time_budget_ms, max_states=max_states)
    except InfeasibleSchedule as exc:
        certificate = getattr(exc, 'retention_certificate', None)
        if certificate is not None:
            PROOFS.append({'input_sha256': fingerprint(data), 'certificate': certificate,
                           'raw_independent_check': check_retention_certificate(data, certificate)})
        raise


def run_age_r109(data, strategy, **kwargs):
    return age_r109_optimize(data, 'age_portfolio', **kwargs)


# The generic manifest records the actual frozen optimizer module, while the
# separate entry SHA records this explicit-strategy adapter itself.
run_age_r109.__module__ = age_r109_optimize.__module__


if __name__ == '__main__':
    research_benchmark.OPTIMIZERS.update(retention=run_retention, age_r109=run_age_r109)
    status = research_benchmark.main()
    name = sys.argv[sys.argv.index('--round') + 1]
    folder = ROOT / 'experiments' / name
    (folder / 'retention-proofs.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in PROOFS), encoding='utf-8')
    (folder / 'retention-entry-provenance.json').write_text(json.dumps({
        'entry_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'frozen_age_baseline': {'path': 'experiments/baseline_age_r109',
            'strategy': 'age_portfolio', 'core_aggregate_sha256': '0c3d19724d85e33ce7bc8cfba24feb94c0bb3a0b3770091be50fd8aaa4b28af4'},
        'scope': 'Explicit iterative feasibility DFS; full frontier requires last consumption; '
                 'ready dead-result dominance; proofs replayed from fresh raw JSON; no COPY optimality',
    }, indent=2) + '\n')
    raise SystemExit(status)
