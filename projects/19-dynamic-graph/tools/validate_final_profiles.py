"""One final strict scale check for both built presets, using retained original C."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,struct,time
from analyze_source import analyze
from evaluate_source import run_runtime,exact_compare
from research_reference import ensure_dense_reference,sha256

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/final-profiles';root.mkdir(exist_ok=True)
    source=project/'fixtures/official_naive_transcribed.c';meta=root/'program.meta';analyze(source,meta,'clang','cholesky');started=time.perf_counter()
    binaries={'local-mingw':project/'build/cholesky_runtime.exe','memory-mingw':project/'build-memory/cholesky_runtime.exe'}
    report={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha256(source),'preset_sha256':sha256(project/'CMakePresets.json'),'binary_sha256':{k:sha256(v)for k,v in binaries.items()},'tool_sha256':sha256(Path(__file__)),'cases':[],'references':[],'contract':'final rebuilt binary exact whole original C files; one execution per profile/workload, no stable performance claim; ordinary dense10000, true band10000w7, M3; owned input destruction/upper export inside compute; real CPU/WS/commit/host counters'}
    destination=root/'scale-report.json'
    def save():report['elapsed_seconds']=time.perf_counter()-started;destination.write_text(json.dumps(report,indent=2)+'\n')
    refs={}
    for n in(4096,10000):
        ip,oracle,proof=ensure_dense_reference(project,n);refs[n]=(ip,oracle);report['references'].append(proof)
    band=project/'artifacts/band-maximum-reference';proof=json.loads((band/'reference-report.json').read_text())
    if not proof['passed']or proof['source_sha256']!=sha256(source)or proof['input_sha256']!=sha256(band/'input.bin')or proof['oracle_sha256']!=sha256(band/'oracle.bin'):raise AssertionError('retained original C band truth changed')
    report['references'].append(proof)
    files=(root/'mixed-input.bin',root/'mixed-oracle.bin')
    for path,column in zip(files,(0,1)):
        with path.open('wb')as output:
            output.write(struct.pack('<I',3))
            for n in(4096,10000,4096):
                with refs[n][column].open('rb')as original:original.read(4);shutil.copyfileobj(original,output)
    report['stream_provenance']={'input_sha256':sha256(files[0]),'oracle_sha256':sha256(files[1]),'bytes':files[1].stat().st_size,'sizes':[4096,10000,4096],'construction':'verified original C payloads concatenated, M only changed'}
    jobs=[('ordinary-dense-10000',*refs[10000]),('band-10000-w7',band/'input.bin',band/'oracle.bin'),('mixed-stream',*files)]
    save()
    for label,ip,oracle in jobs:
        for profile,binary in binaries.items():
            output=root/'final-output.bin';m=run_runtime(binary,meta,ip,output,engine='auto',threads=4,probe_resources=True)
            expected=0 if profile=='local-mingw' or label.startswith('band-')else(3 if label=='mixed-stream'else 1)
            if m['input_buffers_reused']!=expected:raise AssertionError(('final reuse count',label,profile,m))
            if label.startswith('band-')and(m['worker_threads']!=1 or m['selected_engine']!='banded' or m['structure_bandwidth']!=7):raise AssertionError('final structural path did not run as claimed')
            report['cases'].append({'workload':label,'profile':profile,**m,**exact_compare(oracle,output)});save();print(f'PASS final {profile} {label}: {m["compute_ms"]:.3f}ms, WS {m["process_peak_working_set_bytes"]}, reused {m["input_buffers_reused"]}',flush=True);output.unlink()
    for path in files:path.unlink()
    report['passed']=True;save();print(json.dumps({'passed':True,'cases':len(report['cases']),'elapsed_seconds':report['elapsed_seconds'],'report':str(destination)}))
if __name__=='__main__':main()
