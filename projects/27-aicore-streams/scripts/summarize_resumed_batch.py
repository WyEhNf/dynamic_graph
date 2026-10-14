"""Record independent experiment provenance without overwriting old reports."""
import argparse
import hashlib
import json
from pathlib import Path
from compare_research import summarize

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);p.add_argument('--before',type=int)
    args=p.parse_args();base=Path(f'research/batch{args.batch}');report=Path(f'reports/frontier-recovery-batch{args.batch}.json')
    rows=json.loads(report.read_text());result=dict(source_sha256=sha(base/'solution.cpp'),exe_sha256=sha(base/'aicore_bench.exe'),
        input='data/frontier-recovery-batch32.json',input_sha256=sha('data/frontier-recovery-batch32.json'),report=str(report),summary=rows['summary'],
        all_solve_us=sum(c['solve_us'] for c in rows['cases']),all_thread_cpu_us=sum(c['solve_thread_cpu_us'] for c in rows['cases']),
        model_disagreements=sum(not c['models_equal'] for c in rows['cases']),
        recovered=[dict(name=c['name'],n=c['n'],T=c['T'],peak=c['peak_memory']) for c in rows['cases'] if c['pass']],
        cost_scope='One exploratory functional run; not paired performance evidence',case_scope='All 69 R31 known-witness-feasible failures, unchanged complete input objects')
    assert result['model_disagreements']==0
    if args.before:
        result['comparison']=summarize(json.loads(Path(f'reports/frontier-recovery-batch{args.before}.json').read_text()),rows)
    Path(f'reports/frontier-recovery-batch{args.batch}-summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
