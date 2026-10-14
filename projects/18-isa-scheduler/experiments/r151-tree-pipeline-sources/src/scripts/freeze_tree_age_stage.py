"""Freeze sources before each independent tree-age experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--round', required=True); options = parser.parse_args()
    folder = ROOT / 'experiments' / options.round; folder.mkdir(exist_ok=False)
    paths = list((ROOT / 'isa_scheduler').glob('*.py'))
    paths += [ROOT / name for name in ('scripts/tree_raw_oracles.py', 'scripts/research_tree_age_audit.py',
        'scripts/research_tree_age_probe.py', 'scripts/research_tree_attribution.py', 'scripts/research_spine_age_probe.py',
        'scripts/freeze_tree_age_stage.py', 'tests/test_tree_age.py', 'research/level-stage/tree-age-design.md',
        'scripts/diagnose_tree_dfs_gap.py', 'scripts/research_tree_pipeline_gold.py',
        'scripts/research_tree_pipeline_audit.py', 'scripts/research_tree_pipeline_probe.py',
        'tests/test_tree_pipeline.py', 'research/level-stage/tree-pipeline-plan.md')]
    manifest = {}
    for source in paths:
        relative = source.relative_to(ROOT); target = folder / 'src' / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target); manifest[str(relative)] = hashlib.sha256(source.read_bytes()).hexdigest()
    result = {'frozen_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': manifest,
              'aggregate_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
              'scope': 'Actual sources frozen before new tree tests/oracle/probe; default optimizer unchanged'}
    (folder / 'source-provenance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))


if __name__ == '__main__': main()
