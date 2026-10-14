"""Same sequential O2 functional builds; no performance measurements."""
from pathlib import Path
source=Path('scripts/build_batch48.py').read_text(encoding='utf-8').replace('batch48','batch50').replace('R48','R50')
exec(compile(source,'build_batch50_adapted','exec'))
