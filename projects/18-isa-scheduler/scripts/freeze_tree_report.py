"""Freeze the separately rendered tree-stage report and its evidence pointers."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'experiments/r157-tree-stage-summary'
    folder.mkdir(exist_ok=False)
    paths = [ROOT / 'reports/project18-tree-research.tex',
             ROOT / 'reports/project18-tree-research.pdf', Path(__file__)]
    for name in ('r145-tree-age-sources', 'r147-tree-age-probe-sources',
                 'r152-tree-pipeline-final-sources'):
        target = ROOT / 'experiments' / name / 'source-provenance.json'
        if target.exists(): paths.append(target)
    for name in ('r146-tree-age-small120', 'r148-tree-age-old48', 'r149-tree-age-heldout36',
                 'r150-tree-dfs-diagnosis', 'r153-tree-pipeline-gold',
                 'r154-tree-pipeline-old120', 'r155-tree-pipeline-old48',
                 'r156-tree-pipeline-heldout36'):
        target = ROOT / 'experiments' / name / 'evidence-provenance.json'
        if target.exists(): paths.append(target)
    result = {'frozen_utc': datetime.now(timezone.utc).isoformat(),
              'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in paths},
              'report_pages': 4, 'verification': 'Built-in compile success; final XeLaTeX twice exit0; all4 rendered pages inspected',
              'scope': 'Standalone new report. Historical reports, default auto and full336 quality unchanged.'}
    (folder / 'report-provenance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
