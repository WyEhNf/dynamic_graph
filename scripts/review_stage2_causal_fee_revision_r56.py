"""Read-only review of the preserved hand-fee error and corrected static contract."""
import hashlib,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/27-aicore-streams';D=P/'research/batch56'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    freeze=read(D/'fee-erratum-freeze-revision1.json')
    assert sha(D/'fee-erratum-freeze-revision1.json')=='aee815efa4053eb9a976c8235aa75fa1102701d0ebb85368db89f15b50463a69'
    for r in freeze['files']:
        path=Path(r['path']);path=path if path.is_absolute() else P/path
        assert sha(path)==r['sha256'] and path.stat().st_size==r['bytes'],r['path']
    old=read(D/'source-before-gold-freeze.json')
    assert sha(D/'source-before-gold-freeze.json')=='3904f54639a8aa4d44102e5a681c40dff9d54559de641c371660913aa8dfd43e'
    hand=read(D/'literal-hand-trace-revision1.json');ops=hand['operations'];assert len(ops)==64
    spent=0
    for name,fee,total in ops:
        assert fee>0;spent+=fee;assert spent==total,name
    assert ops[6]==['target_visit_unfinished_J2_PREVIOUSLY_OMITTED',1,13]
    assert next(r[2] for r in ops if r[0]=='J2_best_pair_fields')==75
    assert spent==hand['paid_complete_scan']==127
    assert hand['corrected_critical_limits']==[0,3,4,74,75,126,127,128]
    assert sha(D/'literal-hand-trace.json')==hand['initial_error_preserved_sha256']
    assert not hand['candidate_executed'] and not hand['reference_batch_executed']
    assert sha(D/'solution.cpp')=='3a4f184de2759fdcd1cbfd899c5f8029e2f7f2691743ec214a895123db19c21a'
    assert sha(P/'scripts/make_causal_deferral_gold_batch56.py')=='495c6d82a877dd111163f2f636ffac657802e08879041791262d65669414f800'
    outputs=['gold160.json','gold-driver-input.json','literal-charge-gold.json','fixture-qualifier-summary.json']
    assert not any((D/name).exists() for name in outputs)
    result=dict(passed=True,reviewed_unix=time.time(),revision_freeze_sha256=sha(D/'fee-erratum-freeze-revision1.json'),
        first_pair_fields=75,complete_scan=127,paid_rows=64,preserved_initial_error=True,
        scope='Original record-order FIFO Graph/context, LIFO ancestor/descendant scans, all detector charge-before-action paths and independent bigint physical generator reviewed. First hand table omitted unfinished target visit; source and independent Ledger already include it.',
        authorization='Exactly one independent original-DAG/bigint/literal Ledger 160-reference generation; no candidate/compiler/solver. Keep old error and freeze immutable. New gold naturally75/127, not fitted to candidate; root review materialized full gold before compiler.')
    (ROOT/'outputs/stage2-root-causal-fee-revision-r56.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
