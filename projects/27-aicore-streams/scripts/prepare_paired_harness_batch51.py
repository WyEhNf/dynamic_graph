"""Copy historical harness once with a declared host-monitoring-only delta."""
from pathlib import Path

source = Path('scripts/paired_benchmark.py').read_text(encoding='utf-8')
replacements = [
    ('from compare_research import summarize',
     'from compare_research import summarize\nfrom host_sampler_batch51 import HostSampler'),
    ('    started = time.perf_counter()\n    child = subprocess.Popen',
     '    started = time.perf_counter()\n    host = HostSampler()\n    host.sample(force=True)\n    child = subprocess.Popen'),
    ('    while child.poll() is None:\n        if handle:',
     '    while child.poll() is None:\n        host.sample()\n        if handle:'),
    ('    elapsed = time.perf_counter() - started\n    if child.returncode',
     '    elapsed = time.perf_counter() - started\n    host_load = host.finish()\n    output.with_suffix(".host.json").write_text(json.dumps(host_load, indent=2)+"\\n", encoding="utf-8")\n    output.with_suffix(".stdout.txt").write_text(stdout, encoding="utf-8")\n    output.with_suffix(".stderr.txt").write_text(stderr, encoding="utf-8")\n    if child.returncode'),
    ('                peak_working_set_bytes=peak or None, result=result)',
     '                peak_working_set_bytes=peak or None, host_load=host_load,\n                host_report=str(output.with_suffix(".host.json")),\n                host_report_sha256=sha(output.with_suffix(".host.json")), result=result)'),
    ('    result["current_harness_source_sha256"]=sha("src/benchmark.cpp")',
     '    result["current_harness_source_sha256"]=sha("src/benchmark.cpp")\n    result["measurement_driver_sha256"]=sha(__file__)\n    result["host_sampler_sha256"]=sha(Path(__file__).with_name("host_sampler_batch51.py"))\n    result["host_load_scope"]="Pertrial raw host CPU ticks/RAM samples including user background; sampled 0.25 seconds, same monitor both sides; no background subtraction or empty-host claim"'),
]
for before, after in replacements:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
Path('scripts/paired_benchmark_batch51.py').write_text(source, encoding='utf-8')
print('Static harness prepared; no measurements executed', flush=True)
