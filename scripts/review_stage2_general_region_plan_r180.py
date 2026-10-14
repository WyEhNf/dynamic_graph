"""Review general-DAG region contracts and independently replay handwritten witnesses."""
import json,time
from review_stage2_tree_pair_serial_controls import ROOT,P,replay,fingerprint,sha,distance

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def main():
    evidence={}
    for name in ['r180-general-dag-region-static','r181-general-region-counting-static']:
        d=P/'experiments'/name;m=read(d/'source-provenance.json');evidence[name]=sha(d/'source-provenance.json')
        for relative,digest in m['source_sha256'].items():assert sha(P/relative)==digest and sha(d/'src'/relative)==digest
        for relative,digest in m.get('historical_evidence_sha256',{}).items():assert sha(P/relative)==digest
    hand=P/'research/level-stage/general-region-hand11.json';m=read(hand); data=m['input'];key=fingerprint(data)
    verified=[]
    def evaluate(rows,values,symbolic=False):
        history=[];registers=dict(values)
        for row in rows:
            operands=[history[-distance(t)]for t in row.get('inputs',[])]
            if row['op']=='GET':value=registers[row['reg']]
            elif row['op']=='SET':registers[row['reg']]=operands[0];value=None
            elif row['op']=='COPY':value=history[-distance(row['source'])]
            elif symbolic:value=(row['op'],*operands)
            else:value=(operands[0]+operands[1]if row['op']=='ADD'else operands[0]*operands[1])%(2**64)
            history.append(value)
        return registers
    symbolic={c:('initial',c)for c in ['a','b','c','d','e']};expected=evaluate(data['instructions'],symbolic,True)
    tests=[dict(a=2,b=3,c=5,d=7,e=11),dict(a=2**64-1,b=0,c=2**63,d=2**32,e=2**64-3),dict(a=0,b=0,c=0,d=0,e=0)]
    for name in ['baseline','proposed_manual_witness']:
        saved=dict(m[name],input_sha256=key);cost=replay(data,saved);assert cost==m[name]['copies']
        out=m[name]['output']['optimized_instructions'];assert evaluate(out,symbolic,True)==expected
        for values in tests:assert evaluate(out,values)==evaluate(data['instructions'],values)
        verified.append(dict(witness=name,original_nodes=11,physical_rows=len(out),COPY=cost,physical_identity=True,symbolic_registers=True,local_integer_checks=3))
    assert [x['COPY']for x in verified]==[3,1]
    plan=(P/'research/level-stage/general-dag-region-plan.md').read_text(encoding='utf-8');extra=(P/'research/level-stage/general-dag-region-resource-clarification.md').read_text(encoding='utf-8')
    for word in ['32bit','RAW/WAR/WAW','全部ready','20k transition','固定suffix','原identity','500ms']:assert word in plan
    for word in ['prepare_neighbors','20064','size_unsupported','每个ready动作只模拟一次']:assert word in extra
    result=dict(passed=True,reviewed_unix=time.time(),source_freezes=evidence,manual_witness_sha256=sha(hand),manual_complete_witnesses=verified,transition_attempt_cap=20000,expansion_cap=20000,region_cap=64,region_nodes=32,complete_per_region=16,labels_upper=20064,reserve_bytes=512*1024**2,authorization='Implement isolated general-region core/wrapper and predeclared small raw-oracle/contract fixtures plus source/resource-layout freeze; no solver or fullcorpus execution until code/gold/resource review. Retain default/core/336statuses/11pause.',scope='Root reviewed genuine allready originalDAG/sharedroles/hazard/prefix+suffix state contracts and tighter separatelycounted transition cap. Handwritten two complete11node blocks independently physicalidentity/RAW-WAR-WAW and ordered symbolic registers/3local64bit tests verified3to1COPY; not new algorithm gain or officialscore. Actual implementation bytes/completeoutput storage/oracle/partial/reopen controls still require freeze review.')
    (ROOT/'outputs/stage2-root-general-region-plan-r180.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
