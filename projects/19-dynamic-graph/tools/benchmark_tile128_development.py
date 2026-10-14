"""Predeclared same-binary geometry screen on cached independent Cholesky C files."""
import argparse,datetime,hashlib,json,os,statistics,subprocess
from pathlib import Path
from evaluate_source import exact_compare

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--metadata',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--cache-plan',type=Path,required=True);args=p.parse_args()
    root=args.output_dir.resolve()
    if root.exists():raise SystemExit('Refusing to overwrite geometry evidence')
    root.mkdir(parents=True)
    project=Path(__file__).resolve().parents[1]
    cache=json.loads(args.cache_plan.read_text());cases=[]
    def find(value):
        if isinstance(value,dict):
            if 'input' in value and 'oracle' in value and value.get('name') in ('dense-4099','dense-6145'):cases.append(value)
            for v in value.values():find(v)
        elif isinstance(value,list):
            for v in value:find(v)
    find(cache)
    cases.extend([dict(name='dense-8193',input=str(project/'artifacts/stage2-grain128-holdout/dense-8193/input.bin'),
                       oracle=str(project/'artifacts/stage2-grain128-holdout/dense-8193/oracle.bin')),
                  dict(name='dense-10000',input=str(project/'artifacts/maximum-dense-oracle/input.bin'),
                       oracle=str(project/'artifacts/maximum-dense-oracle/oracle.bin'))])
    assert len(cases)==4
    r=dict(passed=False,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      runtime_sha256=hashlib.sha256(args.runtime.read_bytes()).hexdigest(),
      plan='Five AB/BA pairs per shape, 16 workers, full output each process, first pair full original C bytes. '
           'Candidate promotion requires all N>=6144 paired median compute gains>=3%, >=4/5 wins, '
           'and no pair regression>10%. N4099 is a lower-domain control; no default changes before gate.',
      records=[],summary=[])
    def save():(root/'report.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    save()
    for case in cases:
        for pair in range(5):
            for mode in (('auto','128') if pair%2==0 else ('128','auto')):
                out=root/'actual.bin'
                command=[str(args.runtime),'--metadata',str(args.metadata),'--input',case['input'],'--output',str(out),
                  '--engine','tiled','--tile-size',mode,'--threads','16','--scheduler','parallel','--structure','dense']
                x=subprocess.run(command,capture_output=True,text=True,check=True);m=json.loads(x.stdout)
                assert m['worker_threads_max']==16, m
                check=exact_compare(case['oracle'],out) if pair==0 else {'length_equal':out.stat().st_size==Path(case['oracle']).stat().st_size}
                assert check.get('length_equal',True)
                r['records'].append(dict(case=case['name'],pair=pair,mode=mode,command=command,metrics=m,correctness=check));save()
        rows=[x for x in r['records'] if x['case']==case['name']]
        base=[x['metrics']['compute_ms'] for x in rows if x['mode']=='auto'];cand=[x['metrics']['compute_ms'] for x in rows if x['mode']=='128']
        gains=[100*(1-c/b) for b,c in zip(base,cand)]
        summary=dict(case=case['name'],auto_median_ms=statistics.median(base),tile128_median_ms=statistics.median(cand),
           paired_gains_percent=gains,median_paired_gain_percent=statistics.median(gains),wins=sum(x>0 for x in gains))
        r['summary'].append(summary);save();print(json.dumps(summary),flush=True)
    high=[s for s in r['summary'] if s['case']!='dense-4099']
    r.update(passed=True,promotion_gate_passed=all(s['median_paired_gain_percent']>=3 and s['wins']>=4 and min(s['paired_gains_percent'])>=-10 for s in high))
    save();print(json.dumps({'passed':True,'promotion_gate_passed':r['promotion_gate_passed']}),flush=True)

if __name__=='__main__':main()
