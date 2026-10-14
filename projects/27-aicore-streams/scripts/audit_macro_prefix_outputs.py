"""Independent exact original-ID bigint audit of all completed R63 orders."""
from pathlib import Path
import hashlib,json
from validate_macro_prefix_candidate import replay
ROOT=Path(__file__).resolve().parents[1];OUT=Path('G:/Hackathon-stage2-artifacts/project27/20261013/r63')
source=ROOT/'research/batch52/remaining63-input-only.json';result=OUT/'remaining63-helper.json'
cases=json.loads(source.read_text())['cases'];rows=json.loads(result.read_text())['cases'];assert len(cases)==len(rows)==63
records=[]
for case,row in zip(cases,rows):
    assert case['name']==row['name'];h=row['helper'];assert 0<=h['work']<=160000000
    peak=replay(case['nodes'],h['order_ids'],case['hardware']['memory_limit'])
    if h['valid']:assert peak==h['peak'] and peak is not None
    else:assert not h['order_ids'] and peak is None
    records.append({'name':case['name'],'nodes':len(case['nodes']),'valid':h['valid'],'bigint_peak':peak,'work':h['work'],
                    'cpu_us':h['cpu_us'],'wall_us':h['wall_us'],'budget_cutoff':h['exhausted']})
report={'passed':True,'records':records,'total':63,'recovered':sum(r['valid'] for r in records),'remaining':sum(not r['valid'] for r in records),
        'cpu_us':sum(r['cpu_us'] for r in records),'wall_us':sum(r['wall_us'] for r in records),'max_wall_us':max(r['wall_us'] for r in records),
        'scope':'input-only helper complete original orders, independently replayed Python bigint DIRECT lifetime; full API separately tested',
        'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,result,OUT/'selected-driver.exe',ROOT/'research/batch63/single-file-solution.cpp',Path(__file__)]}}
(OUT/'bigint-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('records','sha256')}))
