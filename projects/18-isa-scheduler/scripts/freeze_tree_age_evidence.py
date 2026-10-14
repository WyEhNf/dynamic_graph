"""Freeze existing raw inputs/outputs/reports without changing experiment data."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True); options = parser.parse_args()
    folder = ROOT / 'experiments' / options.round; target = folder / 'evidence-provenance.json'
    if target.exists(): raise FileExistsError(target)
    paths = [p for p in folder.glob('*') if p.is_file()]
    result = {'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'evidence_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'scope': 'Actual completed experiment evidence hashes, not new optimization or proof'}
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'frozen_utc': result['frozen_utc'], 'files': len(paths), 'manifest': str(target.relative_to(ROOT))}))


if __name__ == '__main__': main()
