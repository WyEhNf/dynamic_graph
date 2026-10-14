"""Save actual raw rook branch-set certificates on an exact prior corpus."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from isa_scheduler.model import parse_block
from isa_scheduler.rook_minor import propose_rook_minor, check_rook_minor
from isa_scheduler.evaluation import fingerprint


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True); parser.add_argument('--input', required=True)
    options = parser.parse_args(); folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    cases = [json.loads(line) for line in Path(options.input).read_text().splitlines() if line.strip()]
    payload = ''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases)
    (folder / 'inputs.jsonl').write_text(payload, encoding='utf-8'); records = []; started = perf_counter()
    for case in cases:
        data = case['input']; tick = perf_counter(); certificate = propose_rook_minor(parse_block(data), time_budget_ms=1000)
        proof = check_rook_minor(data, certificate) if certificate else None
        records.append({'sha256': fingerprint(data), 'family': case['family'], 'node_count': len(data['instructions']),
            'bit_width': data['bit_width'], 'certificate': certificate, 'raw_check': proof,
            'status': 'proved_infeasible_identity_model' if proof and proof['verified_infeasible_under_original_identity_model'] else
                      'necessary_bound_only' if proof else 'matcher_no_certificate', 'elapsed_ms': (perf_counter() - tick) * 1000})
    report = {'count': len(cases), 'statuses': dict(Counter(row['status'] for row in records)),
        'elapsed_seconds': perf_counter() - started, 'records': records,
        'corpus_sha256': hashlib.sha256((folder / 'inputs.jsonl').read_bytes()).hexdigest(),
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
                          (Path(__file__), ROOT / 'isa_scheduler/rook_minor.py', ROOT / 'isa_scheduler/minor_bounds.py')},
        'scope': 'Offline data-edge minor only. Model capacity certificate, no output or COPY improvement. Default optimizer unchanged.'}
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'}))


if __name__ == '__main__': main()
