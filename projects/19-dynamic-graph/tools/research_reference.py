"""Reuse a documented original-C oracle, or regenerate it when absent.

Large files are disposable. Cached references are keyed by the actual C source
and input/output SHA256; neither their digest nor matrix contents select kernels.
"""
from pathlib import Path
import hashlib,json,struct,subprocess,time
from datetime import datetime,timezone
from evaluate_source import compile_oracle,make_input

def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb')as stream:
        while block:=stream.read(1024*1024):digest.update(block)
    return digest.hexdigest()

def _shape(path,n):
    if not path.is_file()or path.stat().st_size!=8+8*n*n:return False
    with path.open('rb')as stream:return stream.read(8)==struct.pack('<II',1,n)

def ensure_dense_reference(project,n,gcc='gcc'):
    project=Path(project).resolve()
    if not 3<=n<=10000:raise ValueError('invalid dense reference dimension')
    source=project/'fixtures/official_naive_transcribed.c';source_sha=sha256(source)
    folder=project/'artifacts'/('maximum-dense-oracle'if n==10000 else f'simd-milestone/dense-{n}'if n==4096 else f'tile-milestone/dense-{n}')
    folder.mkdir(parents=True,exist_ok=True);ip=folder/'input.bin';ref=folder/'oracle.bin';manifest=folder/'reference-provenance.json'
    valid=_shape(ip,n)and _shape(ref,n)
    record=None
    if valid and manifest.exists():
        record=json.loads(manifest.read_text(encoding='utf-8'))
        if record['source_sha256']!=source_sha:valid=False
        elif (sha256(ip),sha256(ref))!=(record['input_sha256'],record['oracle_sha256']):raise ValueError('cached reference SHA changed; remove both files and regenerate')
    elif valid:
        # Import existing completed milestone evidence once, with the original
        # source provenance checked and oracle digest matched before reuse.
        milestone=project/'artifacts'/('extended-milestone'if n==10000 else 'simd-milestone'if n==4096 else 'tile-milestone')
        metadata=milestone/'page/program.meta';analysis=milestone/'page/program.analysis.json'
        text=metadata.read_text(encoding='utf-8')if metadata.exists()else''
        metadata_sha=next((line.split('=',1)[1]for line in text.splitlines()if line.startswith('source_sha256=')),None)
        if metadata_sha is None and analysis.exists():metadata_sha=json.loads(analysis.read_text(encoding='utf-8')).get('source_sha256')
        report_path=milestone/('extended-report.json'if n==10000 else 'simd-report.json'if n==4096 else 'tile-report.json')
        report=json.loads(report_path.read_text(encoding='utf-8'))if report_path.exists()else{}
        matches=[r for r in report.get('performance',[])if r['n']==n and r.get('byte_identical')]
        valid=bool(report.get('passed')and matches and metadata_sha==source_sha)
        if valid:
            actual=sha256(ref)
            if any(r['sha256']!=actual for r in matches):raise ValueError('legacy original-C reference does not match completed evidence')
            record={'source_sha256':source_sha,'input_sha256':sha256(ip),'oracle_sha256':actual,'imported_evidence':str(report_path),'oracle_wall_ms':matches[0].get('oracle_wall_ms'),'input_generation_ms':matches[0].get('input_generation_ms')}
    if not valid:
        print(f'REGENERATE dense N={n}: full original-C oracle; N10000 can take about 8 minutes locally',flush=True)
        begin=time.perf_counter();make_input(ip,[n]);input_ms=(time.perf_counter()-begin)*1000
        oracle=compile_oracle(source,'cholesky',folder/'oracle-build',gcc)
        begin=time.perf_counter();subprocess.run([str(oracle),str(ip),str(ref),'32'],check=True);oracle_ms=(time.perf_counter()-begin)*1000
        if not _shape(ip,n)or not _shape(ref,n):raise ValueError('new reference has malformed binary shape')
        record={'source_sha256':source_sha,'input_sha256':sha256(ip),'oracle_sha256':sha256(ref),'oracle_wall_ms':oracle_ms,'input_generation_ms':input_ms,'oracle':'actual source separately GCC -O2 -fno-fast-math -ffp-contract=off'}
    record.update({'n':n,'bytes':ref.stat().st_size,'checked_at_utc':datetime.now(timezone.utc).isoformat()})
    manifest.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return ip,ref,record
