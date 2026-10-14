"""Independent post-run ownership and all compressed/decoded bytes audit."""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'projects/18-isa-scheduler/experiments/r194-mobile-backbone-small'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    m=read(D/'artifact-provenance.json');root=read(ROOT/'outputs/stage2-root-mobile-backbone-actual-r194.json')
    assert m['report_SHA']==root['report_sha256']==sha(D/'report.json') and m['count']==84
    for k in ['owner_contract_execution','owner_84_execution']:
        r=m[k];assert r['exit_code']==0 and sha(r['actual_log'])==r['log_SHA']
    assert m['owner_contract_execution']['tests']==15 and m['owner_84_execution']['tool_chunk']=='6337d3'
    compressed=decoded=0
    for r in m['files']:
        p=Path(r['absolute_path']);assert p.drive.upper()=='G:' and sha(p)==r['compressed_SHA'] and p.stat().st_size==r['compressed_bytes']
        h=hashlib.sha256();size=count=maximum=0
        with gzip.open(p,'rb') as f:
            for blob in f:h.update(blob);size+=len(blob);count+=1;maximum=max(maximum,len(blob))
        assert h.hexdigest()==r['decoded_SHA'] and size==r['decoded_bytes'] and count==r['lines'] and maximum==r['maximum_line_bytes']
        compressed+=p.stat().st_size;decoded+=size
    assert len(m['files'])==m['gzip_file_count']==259 and compressed==m['compressed_total_bytes']==445528 and decoded==m['decoded_total_bytes']==3305854
    result=dict(passed=True,artifact_index_sha256=sha(D/'artifact-provenance.json'),actual_contracts_tool_chunk='01f83d',actual_batch_tool_chunk='6337d3',terminal_exit_code=0,gzip_files=259,compressed_bytes=compressed,decoded_bytes=decoded,measured_process_lifetime_peak_RSS_bytes=m['measured_process_lifetime_peak_RSS_bytes'],scope='All259 actual gzip artifacts independently hashed compressed and decoded, owner logs and84 report bound; RSS is measured process lifetime peak, not a generic memory guarantee.')
    (ROOT/'outputs/stage2-root-mobile-backbone-artifacts-r194.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
