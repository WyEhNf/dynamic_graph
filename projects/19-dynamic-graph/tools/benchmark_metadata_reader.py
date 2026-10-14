"""Actual read_metadata comparison; loader scope is separate from matrix compute."""
import argparse,datetime,hashlib,json,os,statistics,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--candidate-build',type=Path,required=True);p.add_argument('--metadata-root',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--cxx',default='g++')
    args=p.parse_args();root=args.output_dir.resolve();root.mkdir(parents=True,exist_ok=False)
    project=Path(__file__).resolve().parents[1];sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    cores={}
    for name,build in [('baseline',args.baseline_build),('candidate',args.candidate_build)]:
        core=build/'libcholesky_core.a';cores[name]=sha(core)
        subprocess.run([args.cxx,'-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-I'+str(project/'include'),
                        str(project/'tools/metadata_load_probe.cpp'),str(core),'-pthread','-o',str(root/(name+'.exe'))],check=True)
    r=dict(passed=False,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),core_sha256=cores,
           plan='Seven fresh-process AB/BA pairs per case, 1024 full reader calls per process, first read untimed. '
                'Includes open/read/parse/close/destruction. Excludes matrix execution; not a cold-start result. '
                'Gate: all compact cases paired median gain>=10%, named controls regression<=5%.',records=[],summary=[])
    def save():(root/'report.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    save()
    for source in ('scalar','page','blocked'):
        for wire in ('3-table','2-dag'):
            meta=args.metadata_root/source/(wire+'.meta');label=source+'/'+wire
            for pair in range(7):
                for mode in (('baseline','candidate') if pair%2==0 else ('candidate','baseline')):
                    x=subprocess.run([str(root/(mode+'.exe')),str(meta),'1024'],capture_output=True,text=True,check=True)
                    r['records'].append(dict(case=label,pair=pair,variant=mode,metadata_sha256=sha(meta),metrics=json.loads(x.stdout)));save()
            rows=[x for x in r['records'] if x['case']==label]
            base=[x['metrics'] for x in rows if x['variant']=='baseline'];cand=[x['metrics'] for x in rows if x['variant']=='candidate']
            assert len({m['parsed_hash'] for m in base+cand})==1 and len({m['observed'] for m in base+cand})==1
            gains=[100*(1-c['milliseconds']/b['milliseconds']) for b,c in zip(base,cand)]
            summary=dict(case=label,baseline_median_ms=statistics.median(m['milliseconds'] for m in base),
                         candidate_median_ms=statistics.median(m['milliseconds'] for m in cand),paired_reductions_percent=gains,
                         median_paired_reduction_percent=statistics.median(gains),wins=sum(g>0 for g in gains))
            r['summary'].append(summary);save();print(json.dumps(summary),flush=True)
    r.update(passed=True,gate_passed=all(s['median_paired_reduction_percent']>=(10 if '/3-' in s['case'] else -5) for s in r['summary']))
    save()

if __name__=='__main__':main()
