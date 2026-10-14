"""Literal independent-event controls; auxiliary unit checks, not corpus records."""
import hashlib
import json
import subprocess
from pathlib import Path
from generate_cases import case, hardware, node, serial_witness


def main():
    h=hardware(streams=4,memory=100,record=0,wait=0)
    h.update(aic_core_num=128,aiv_core_num=128)
    output=[node(17,'AIC',1,3,40,20),node(93,'AIC',1,7,40,20),node(41,'AIC',1,11,40,20)]
    witness,_,_=serial_witness(output)
    records=[case('literal_workspace_plus_output_clique',h,output,21,witness)]
    def two_flows(nodes):
        return {'streams':[{'tasks':[{'op_id':v['id'],'wait_before':[],'record_after':-1}]} for v in nodes]}
    half_hw=dict(h,aic_core_num=8,aiv_core_num=8)
    half=[node(17,'AIC',4,3,50,0),node(93,'AIC',4,7,50,0)]
    records.append(case('literal_exact_half_overlap',half_hw,half,7,two_flows(half)))
    dual=[node(17,'AIC',5,3,0,0),node(93,'AIV',5,7,0,0)]
    records.append(case('literal_distinct_pool_overlap',half_hw,dual,7,two_flows(dual)))
    source=Path('reports/resource-liveness-input-batch31.json')
    source.write_text(json.dumps(dict(format='aicore-local-v1',cases=records)))
    report=Path('reports/resource-liveness-batch31.json')
    subprocess.run([str(Path('research/batch31/aicore_bench.exe').resolve()),'--input',str(source),'--output',str(report)],check=True)
    rows=json.loads(report.read_text())['cases']
    for r,(T,P) in zip(rows,[(21,100),(7,100),(7,0)]):
        assert r['pass'] and r['models_equal'] and (r['T'],r['peak_memory'])==(T,P),r['name']
    proof=dict(checked=3,source_sha256=hashlib.sha256(Path('research/batch31/solution.cpp').read_bytes()).hexdigest(),
        input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Auxiliary literal unit controls, excluded from 1193 benchmark record count',
        expected_T_peak=[[21,100],[7,100],[7,0]],report=str(report))
    Path('reports/resource-liveness-audit-batch31.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps(proof))


if __name__=='__main__':main()
