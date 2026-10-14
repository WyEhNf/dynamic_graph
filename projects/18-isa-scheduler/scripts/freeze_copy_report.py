"""Freeze the separately compiled R125--R143 report, never replace history."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / 'experiments/r143-root-lifetime-summary/report-provenance.json'
    if destination.exists(): raise FileExistsError(destination)
    paths = ['reports/project18-copy-research.tex', 'reports/project18-copy-research.pdf',
             'experiments/r135-root-potential-sources/source-provenance.json',
             'experiments/r142-lifetime-sources/source-provenance.json',
             'experiments/r143-root-lifetime-summary/report.json']
    result = {'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        'compiled': 'Built-in compiler success before command-space correction; final local XeLaTeX exit0; no overfull/undefined warnings',
        'render_review': 'All five pages at125dpi inspected; final pages4/5 reinspected after command-space correction',
        'scope': 'R125--R143 separate research; default auto and R109 whole quality unchanged'}
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
