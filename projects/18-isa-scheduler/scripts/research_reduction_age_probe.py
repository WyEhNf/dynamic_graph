"""Use the existing four-check paired harness for explicit age-search probes.

All ordinary research_benchmark arguments are accepted. Core defaults do not
change. These candidates have no whole-DAG fallback and all failures remain.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import research_benchmark
from isa_scheduler.model import parse_block
from isa_scheduler.reduction_age import schedule_reduction_age
from isa_scheduler.evaluation import fingerprint

DETAILS = []


def run_age(data, strategy, time_budget_ms=1000, max_states=30000, pending=1, boundary_beam=6, label='age_inline', **kwargs):
    output = schedule_reduction_age(parse_block(data), time_budget_ms=time_budget_ms,
                                    max_states=min(max_states, 4000), max_pending=pending, beam_width=boundary_beam)
    DETAILS.append({'input_sha256': fingerprint(data), 'variant': label,
                    'stats': {key: value for key, value in output['stats'].items() if key != 'original_order'}})
    return output


if __name__ == '__main__':
    research_benchmark.OPTIMIZERS.update(age_inline=run_age,
        age_pair=lambda data, strategy, **kwargs: run_age(data, strategy, pending=2, label='age_pair', **kwargs),
        age_fast=lambda data, strategy, **kwargs: run_age(data, strategy, boundary_beam=1, label='age_fast', **kwargs),
        age_tight=lambda data, strategy, **kwargs: run_age(data, strategy, boundary_beam=2, label='age_tight', **kwargs))
    exit_status = research_benchmark.main()
    # The generic harness records its own SHA. Also freeze the actual candidate
    # entry point and parameters rather than pretending its wrapper is absent.
    name = sys.argv[sys.argv.index('--round') + 1] if '--round' in sys.argv else 'r1'
    folder = ROOT / 'experiments' / name
    (folder / 'age-details.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in DETAILS), encoding='utf-8')
    (folder / 'age-entry-provenance.json').write_text(json.dumps({
        'entry_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'direct restricted candidate, no fallback; age_inline/pair pending limits 1/2, boundary beam6; age_fast/tight pending1 beam1/2; per-column states <=4000; greedy COPY; no global optimality claim',
    }, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(exit_status)
