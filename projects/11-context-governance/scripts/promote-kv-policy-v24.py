"""Promote the frozen v24 package only after its complete real-GPU validation."""
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    candidate = ROOT / 'adapters/research-v24/context_governance'
    provenance = json.loads((candidate.parent / 'provenance.json').read_text(encoding='utf-8'))
    evidence_path = ROOT / 'artifacts/kv-policy-api-compatibility-v24.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    if (evidence.get('status') != 'complete'
            or evidence.get('short_timed_calls') != 48
            or not evidence.get('all_short_complete_greedy_ids_equal')
            or not evidence.get('long_run', {}).get('exact_historical_complete_ids_hash_equal')
            or not evidence.get('model_files_verified_at_finalization')):
        raise ValueError('Require complete real-GPU API/token validation')
    expected = provenance['candidate_source_sha256']
    if len(expected) != 25 or {p.name for p in candidate.glob('*.py')} != set(expected):
        raise ValueError('Candidate module inventory changed')
    active = ROOT / 'src/context_governance'
    frozen_before = ROOT / 'adapters/research-v17d-source'
    for name, digest in expected.items():
        if sha(candidate / name) != digest or evidence['source_sha256_at_start'][name] != digest:
            raise ValueError('GPU-tested candidate bytes changed: ' + name)
        if sha(active / name) != sha(frozen_before / name):
            raise ValueError('Unexpected active source change before promotion: ' + name)
    record_path = ROOT / 'artifacts/v24-promotion.json'
    if record_path.exists():
        raise FileExistsError(record_path)
    before = {name: sha(active / name) for name in expected}
    for name in expected:
        shutil.copyfile(candidate / name, active / name)
    after = {name: sha(active / name) for name in expected}
    if after != expected:
        raise AssertionError('Promoted bytes differ from the GPU-tested package')
    record = {'promoted_unix': time.time(), 'scope': 'Exact frozen package promotion; historical reports and defaults preserved',
              'before_source_sha256': before, 'after_source_sha256': after,
              'gpu_evidence_sha256': sha(evidence_path),
              'candidate_provenance_sha256': sha(candidate.parent / 'provenance.json'),
              'script_sha256': sha(Path(__file__)), 'defaults': {'generation': 'single', 'kv_cache_policy': 'resident',
                                                               'public_examples_protocol': 'literal-v17'}}
    record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({'promoted_modules': len(after), 'evidence': str(record_path)}))


if __name__ == '__main__':
    main()
