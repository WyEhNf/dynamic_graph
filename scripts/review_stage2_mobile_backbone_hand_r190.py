"""Independent complete witness replay and a zero-COPY impossibility bound."""
import hashlib,json
from pathlib import Path
from review_stage2_spine_extensions import replay,fingerprint
from review_stage2_general_region_actual_r185 import evaluate
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'projects/18-isa-scheduler/research/level-stage'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=D/'mobile-backbone-hand45.json'
    assert sha(p)=='ae1d51b588bba72b6f1f4ad840dc0fa54400195f0dfc474ca852e43a3c17b7eb'
    d=json.loads(p.read_text());data=d['input'];original=data['instructions'];names=sorted({r['reg'] for r in original if 'reg' in r});symbols={n:('reg',n) for n in names}
    assert len(original)==45 and data['bit_width']==2
    before,after=d['baseline'],d['manual_mobile_witness'];costs=[]
    for saved in [before,after]:
        costs.append(replay(data,dict(saved,input_sha256=fingerprint(data))))
        rows=saved['output']['optimized_instructions']
        assert evaluate(original,symbols)==evaluate(rows,symbols)
        for bits,signed in [(8,True),(16,False),(32,True)]:
            for seed in [19001,19002,19003]:
                values={n:(seed-37*i)%(1<<bits) for i,n in enumerate(names)}
                if signed:values={n:(v-(1<<bits) if v>=1<<(bits-1) else v) for n,v in values.items()}
                assert evaluate(original,values,bits,signed)==evaluate(rows,values,bits,signed)
    assert costs==[13,0] and before['original_order']==list(range(45))
    assert after['original_order']==list(range(3,43))+[0,1,2,43,44]
    assert original[0]['op']=='GET' and original[43]['op']=='MULW' and original[43]['inputs']==['t#43','t#43']
    intervals=[]
    for left in range(45):
        for right in range(left,min(45,left+32)):
            assert not (left<=0<=right and left<=43<=right)
            latest_G=right if left<=0<=right else 0
            earliest_M=left if left<=43<=right else 43
            gap=earliest_M-latest_G
            assert gap>=12>4
            intervals.append(dict(left=left,right=right,minimum_original_gap=gap))
    assert len(intervals)==944
    doc=dict(passed=True,hand_sha256=sha(p),whole_outputs=2,physical_COPY_before_after=costs,symbolic_checks=2,integer_checks=18,continuous_intervals=944,min_producer_consumer_gap=12,window=4,
        proof='With zero COPY, physical and original ranks coincide. A length<=32 interval moves each member at most31 slots and cannot contain both GET0 and MULW43. Even ignoring all readiness constraints, their minimum gap is12>W4. MULW43 must use original GET0 twice; zero COPY is impossible for any single such interval with fixed outside order. Added retained prefix COPY only strengthens this impossibility.',
        prior_root_review_failure='af1770 exit1: root assumed mobile-before-backbone but the frozen valid witness uses backbone-before-mobile; corrected reader only, witness unchanged.',
        scope='Manual witness and neighborhood expressiveness only; no new solver, corpus gain or official Level claim; symbolic evaluator treats MULW as ordered syntax, integer evaluator checks original/output equality.')
    target=ROOT/'outputs/stage2-root-mobile-backbone-hand-r190.json';target.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8');print(json.dumps(doc))
if __name__=='__main__':main()
