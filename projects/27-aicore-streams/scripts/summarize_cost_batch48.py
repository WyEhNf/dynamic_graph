"""Schema-preserving adaptation of the audited R45 all-record summarizer.

Run only after actual authorized R48 measurement terminal. This adapter
does not initiate a benchmark or modify any existing raw measurement.
"""
from pathlib import Path
source=Path('scripts/summarize_cost_batch45.py').read_text(encoding='utf-8')
source=source.replace('batch45','batch48').replace('batch44','batch45')
source=source.replace('Parent observed about1.32GiB available RAM and active user applications; not a complete-window sample','User applications remain;trial availability and busy fraction unmeasured by unchanged harness;no empty-host claim')
exec(compile(source,'summarize_cost_batch48_adapted','exec'))
