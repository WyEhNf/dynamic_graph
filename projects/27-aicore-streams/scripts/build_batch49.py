"""Same sequential functional O2 drivers as R48, candidate source49 only."""
from pathlib import Path
source=Path('scripts/build_batch48.py').read_text(encoding='utf-8').replace('batch48','batch49').replace('R48','R49')
exec(compile(source,'build_batch49_adapted','exec'))
