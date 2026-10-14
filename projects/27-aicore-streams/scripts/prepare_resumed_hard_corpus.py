"""All original 202 difficult records, unchanged, for paired whole-corpus runs."""
import hashlib
import json
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    old=json.loads(Path('reports/final-hard-batch31.json').read_text());cases=[];rows=[];sources={}
    for check in old['checks'].values():
        path=check['input'];doc=json.loads(Path(path).read_text())
        assert sha(path)==check['input_sha256']
        cases.extend(doc['cases']);rows.extend(json.loads(Path(check['report']).read_text())['cases'])
        sources[path]=sha(path)
    assert len(cases)==len(rows)==202 and len({c['name'] for c in cases})==202
    p=Path('data/hard-corpus-resumed.json');p.write_text(json.dumps(dict(format='aicore-local-v1',cases=cases)),encoding='utf-8')
    Path('reports/hard-corpus-r31-reference.json').write_text(json.dumps(dict(format='aicore-results-v1',cases=rows,summary=dict(total=202,passed=133,failed=69))))
    evidence=dict(records=202,case_policy='Exact objects of all old difficult suites; no generator changes, deleted cases or deadline/witness modification',
        sources=sources,input_sha256=sha(p),prior_report_sha256=sha('reports/final-hard-batch31.json'))
    Path('reports/hard-corpus-resumed-provenance.json').write_text(json.dumps(evidence,indent=2))
    print('202 unchanged difficult records ready')

if __name__=='__main__':main()
