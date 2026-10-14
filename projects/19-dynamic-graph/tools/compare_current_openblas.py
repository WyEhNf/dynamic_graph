"""Current release versus actual OpenBLAS; five fresh-process AB/BA pairs.

Both dense and LAPACK band algorithms are measured. Source bit equality is
separate from numerical error; wrapper and pure factor time are separate.
"""
import argparse,datetime,hashlib,json,os,shutil,statistics,subprocess,sys
from pathlib import Path

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(8*1024*1024),b''):digest.update(part)
    return digest.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--blas-python',required=True);p.add_argument('--previous-report',type=Path,required=True)
    p.add_argument('--metadata',type=Path,required=True);args=p.parse_args()
    project=Path(__file__).resolve().parents[1];root=args.output_dir.resolve();root.mkdir(parents=True,exist_ok=False)
    runtime=project/'build/cholesky_runtime.exe'
    release=json.loads((project/'reports/project19-development-validation-2026-10-14.json').read_text())
    expected=release['release']['profiles']['local']['runtime_sha256'];assert sha(runtime)==expected
    previous=json.loads(args.previous_report.read_text());cases=previous['plan']['inputs']
    for case in cases:
        assert sha(case['input'])==case['input_sha256'] and sha(case['oracle'])==case['oracle_sha256']
    for file in ['compare_current_openblas.py','openblas_comparison_case.py']:
        shutil.copyfile(project/'tools'/file,root/file)
    r=dict(status='running',runtime_sha256=expected,metadata_sha256=sha(args.metadata),
       started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
       plan=dict(cases=cases,pairs=5,threads=16,order='AB/BA alternating fresh processes, no samples dropped',
         timing='No warmup, matrix I/O excluded. Native compute includes actual finite/structure scans, graph, factor/export. '
                'Library factor excludes finite checks, packing and cleanup; wrapper includes them. Band library takes explicit KD7; '
                'its wrapper excludes certifying off-band zeros. Neither library timer includes source compilation or symbolic Metadata.',
         limits='Shared host, no affinity or thermal isolation. Results compare one installed OpenBLAS 0.3.30 build, not all best libraries.'),
       records=[],summary=[])
    def save():(root/'report.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    save()
    env=dict(os.environ,PATH='E:/mingw64/bin;'+os.environ.get('PATH',''),PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    for case in cases:
        for pair in range(5):
            for variant in (('native','blas') if pair%2==0 else ('blas','native')):
                tag=f'{case["label"]}-{pair}-{variant}';output=root/'current-output.bin'
                command=[str(runtime),'--metadata',str(args.metadata),'--input',case['input'],'--output',str(output),
                         '--scheduler','parallel','--threads','16'] if variant=='native' else [
                         args.blas_python,str(root/'openblas_comparison_case.py'),'--input',case['input'],'--oracle',case['oracle'],'--threads','16','--kind',case['kind']]
                run=subprocess.run(command,env=env,capture_output=True,text=True,timeout=180,check=True)
                (root/(tag+'.stdout')).write_text(run.stdout);(root/(tag+'.stderr')).write_text(run.stderr)
                metrics=json.loads(run.stdout);exact=None
                if variant=='native':
                    exact=sha(output);assert exact==case['oracle_sha256']
                    assert metrics['worker_threads_max']==(1 if case['kind']=='band7' else 16)
                else:assert metrics['threads_actual']==16 and metrics['info']==0
                r['records'].append(dict(case=case['label'],pair=pair,variant=variant,command=command,
                  metrics=metrics,native_original_c_file_sha256=exact));save()
        rows=[x for x in r['records'] if x['case']==case['label']]
        native=[x['metrics'] for x in rows if x['variant']=='native'];blas=[x['metrics'] for x in rows if x['variant']=='blas']
        median=lambda values,key:statistics.median(x[key] for x in values)
        native_times=[x['compute_ms'] for x in native];blas_times=[x['factor_ms'] for x in blas]
        wrappers=[x['wrapper_ms'] for x in blas]
        summary=dict(case=case['label'],native_compute_median_ms=median(native,'compute_ms'),native_kernel_median_ms=median(native,'kernel_ms'),
             blas_factor_median_ms=median(blas,'factor_ms'),blas_wrapper_median_ms=median(blas,'wrapper_ms'),
             native_compute_samples_ms=native_times,blas_factor_samples_ms=blas_times,blas_wrapper_samples_ms=wrappers,
             paired_compute_over_factor=[a/b for a,b in zip(native_times,blas_times)],
             paired_compute_over_wrapper=[a/b for a,b in zip(native_times,wrappers)],
             median_paired_compute_over_factor=statistics.median(a/b for a,b in zip(native_times,blas_times)),
             median_paired_compute_over_wrapper=statistics.median(a/b for a,b in zip(native_times,wrappers)),
             native_bit_exact_all5=True,blas_bit_mismatches_lower=[x['bit_mismatches_lower'] for x in blas],
             blas_relative_factor_error=[x['relative_frobenius_error_to_C'] for x in blas],
             blas_config=blas[0]['config'],blas_core=blas[0]['core'],blas_dll_sha256=blas[0]['dll_sha256'])
        r['summary'].append(summary);save();print(json.dumps(summary),flush=True)
    assert sha(runtime)==expected
    r.update(status='completed',passed=True,processes=len(r['records']),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save()

if __name__=='__main__':main()
