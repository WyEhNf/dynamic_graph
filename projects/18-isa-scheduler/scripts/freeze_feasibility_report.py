"""Freeze the independent report after built-in and XeLaTeX compilation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / 'experiments/r122-symmetry-sources/report-provenance.json'
    if destination.exists(): raise FileExistsError(destination)
    paths = ['reports/project18-feasibility-research.tex', 'reports/project18-feasibility-research.pdf']
    data = {'frozen_utc': datetime.now(timezone.utc).isoformat(),
        'report_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
        'compiled': 'Built-in desktop compiler success; local XeLaTeX twice exit0',
        'render_review': '5 pages at100dpi; all pages inspected, changed final1/4/5 reinspected; no overfull/undefined warnings',
        'scope': 'R110--R122 offline feasibility only; R109 quality untouched; default auto unchanged'}
    destination.write_text(json.dumps(data, indent=2) + '\n'); print(json.dumps(data))


if __name__ == '__main__': main()
