"""Audit frozen general-region implementation and run its declared contracts."""
import ast, hashlib, json, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/18-isa-scheduler'
D=P/'experiments/r183-general-region-reserve-prepared'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    m=json.loads((D/'source-provenance.json').read_text(encoding='utf-8'))
    assert sha(D/'source-provenance.json')=='0971100964e84d5194d65b9a6dd68df98fb80d37b3ef752a50d209662ee63d50'
    for row in m['source_files']:
        assert sha(P/row['path'])==row['sha256']==sha(D/'source'/row['path'])
        assert (P/row['path']).stat().st_size==row['bytes']
        if row['path'].endswith('.py'): ast.parse((P/row['path']).read_text(encoding='utf-8'))
    assert sha(D/'inputs.jsonl')==m['input_sha256']
    inputs=[json.loads(s) for s in (D/'inputs.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(inputs)==80 and all(5<=len(x['instructions'])<=9 for x in inputs)
    assert set(x['bit_width'] for x in inputs)=={2,3,4,5}
    oracle=ast.parse((P/'scripts/raw_general_region_oracle.py').read_text(encoding='utf-8'))
    assert all(not isinstance(x,ast.ImportFrom) or not (x.module or '').startswith('isa_scheduler') for x in ast.walk(oracle))
    command=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_general_region_contracts.py','-v']
    run=subprocess.run(command,cwd=P,capture_output=True,text=True)
    log=ROOT/'outputs/stage2-root-general-region-contracts-r183.log'
    log.write_text(run.stdout+run.stderr,encoding='utf-8')
    assert run.returncode==0 and 'Ran 10 tests' in run.stderr
    result=dict(passed=True,reviewed_unix=time.time(),source_manifest_sha256=sha(D/'source-provenance.json'),
        source_files=len(m['source_files']),source_aggregate_sha256=m['source_aggregate_sha256'],
        input_sha256=m['input_sha256'],frozen_inputs=80,contracts=10,actual_contract_exit=run.returncode,
        actual_command=command,contract_log_sha256=sha(log),
        code_review=['full original identities and RAW/WAR/WAW readiness','latest-age roles include all future consumers',
            'fixed physical prefix and full suffix restoration before sink','immutable low-g labels and separately charged transitions',
            'independent all-history old/early COPY raw oracle','actual input UTF8 sizes and disk preflight/after-saved-complete reserve'],
        authorization='Prepare runner for only frozen80 tiny raw-oracle inputs plus hand11, all complete proposal physical/symbolic/integer checks and independent label/frontier replay; rootreview runner before actual solver/oracle execution. No full336/default integration.',
        scope='Implementation source review and ten actual contract tests only. No new algorithm quality, raw-oracle result, official Level or RSS/performance claim.')
    (ROOT/'outputs/stage2-root-general-region-source-r183.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__': main()
