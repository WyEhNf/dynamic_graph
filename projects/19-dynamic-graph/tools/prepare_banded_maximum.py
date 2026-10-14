"""One real N10000 banded input with an independently compiled original C oracle."""
from pathlib import Path
import hashlib,json,subprocess,time
from datetime import datetime,timezone
from evaluate_source import compile_oracle
from research_reference import sha256
from structured_workloads import make_workload

def main():
    project=Path(__file__).resolve().parent.parent;root=project/'artifacts/band-maximum-reference';root.mkdir(exist_ok=True);source=project/'fixtures/official_naive_transcribed.c';ip=root/'input.bin';ref=root/'oracle.bin';started=time.perf_counter()
    record={'passed':False,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'n':10000,'width':7,'workload':'exact band-limited diagonally-dominant SPD, alternating off-band signed zeros; NOT general dense','source_sha256':sha256(source),'oracle':'actual original source GCC -O2 -fno-fast-math -ffp-contract=off'}
    def save():record['elapsed_seconds']=time.perf_counter()-started;(root/'reference-report.json').write_text(json.dumps(record,indent=2)+'\n')
    save();begin=time.perf_counter();make_workload(ip,[10000],'band',7);record['input_generation_ms']=(time.perf_counter()-begin)*1000;record['input_sha256']=sha256(ip);save()
    oracle=compile_oracle(source,'cholesky',root/'oracle-build','gcc');record['oracle_binary_sha256']=sha256(oracle);print('BEGIN real original-source C banded N10000 oracle, full 800MB layout',flush=True)
    begin=time.perf_counter();subprocess.run([str(oracle),str(ip),str(ref),'32'],check=True);record['oracle_wall_ms']=(time.perf_counter()-begin)*1000
    record['bytes']=ref.stat().st_size;record['oracle_sha256']=sha256(ref);record['passed']=True;save();print(json.dumps(record),flush=True)

if __name__=='__main__':main()
