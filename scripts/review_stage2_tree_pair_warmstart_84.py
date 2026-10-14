"""Root full84 denominator/budget/output audit, including worse/partial outlets."""
import json
import time
from collections import Counter
from fractions import Fraction
from review_stage2_spine_extensions import ROOT,replay,fingerprint,read_lines,sha

P=ROOT/'projects/18-isa-scheduler';D=P/'experiments/r164-tree-pair-warmstart-84'


def main():
    evidence={}
    def read(path):
        evidence[path.relative_to(ROOT).as_posix()]=sha(path)
        return json.loads(path.read_text())
    source=read(D/'source-provenance.json')
    for name,digest in source['source_sha256'].items():assert sha(D/'src'/name)==digest
    for name,digest in source['baseline_evidence_sha256'].items():assert sha(P/name)==digest
    for name,digest in read(D/'evidence-provenance.json')['evidence_sha256'].items():assert sha(P/name)==digest
    report=read(D/'report.json');cases={fingerprint(r['input']):r for r in read_lines(D/'inputs.jsonl')}
    assert len(cases)==len(report['records'])==84
    assert report['source_parameters']==dict(total_time_budget_ms_each_input=500,total_processed_states_each_input=20000,outlets_each_pair=16,parent_nodes_max=96)
    groups={'old48':'r155-tree-pipeline-old48','new36':'r156-tree-pipeline-heldout36'}
    oldrows={group:{r['sha256']:r for r in read(P/'experiments'/name/'report.json')['records']} for group,name in groups.items()}
    sums=Counter();statuses=Counter();outcomes=Counter();means={k:[] for k in ('before_output','after_output','before_original','after_original')}
    replays=0;alloutlets=0;improved=[];budgetpartial=[]
    def check(data,record):
        nonlocal replays
        record=dict(record,input_sha256=fingerprint(data));cost=replay(data,record);replays+=1
        if 'copies' in record:assert cost==record['copies']
        return cost
    for row in report['records']:
        key=row['sha256'];case=cases[key];data=case['input'];group=row['group']
        assert row['before_status']==row['after_status']==oldrows[group][key]['after_status']
        statuses[row['after_status']]+=1;outcomes[row['attempt']['outcome']]+=1
        files=list(D.glob(key[:16]+'-parent*-candidate*-output.json'))
        assert len(files)==row['attempt']['completed_output_files']
        costs=[check(data,read(path)) for path in files];alloutlets+=len(files)
        stats=row['attempt'].get('stats')
        if stats:
            assert stats['parameters']==dict(total_time_budget_ms=500,total_processed_state_budget=20000,max_outcomes_each_pair=16,max_parent_nodes=96)
            assert 0<=stats['processed_states']<=20000
            assert sum(a['processed_states'] for a in stats['attempts'])==stats['processed_states']
            if row['attempt']['outcome']=='partial_budget':budgetpartial.append(dict(sha256=key,states=stats['processed_states'],completed_outputs=len(files)))
        if row['after_status']!='verified':
            assert not files and row['before_copies'] is None and row['after_copies'] is None
            continue
        before=read(D/(key[:16]+'-baseline-output.json'));after=read(D/(key[:16]+'-output.json'))
        prior=read(P/'experiments'/groups[group]/(key[:16]+'-output.json'))
        assert before==prior
        b,a=check(data,before),check(data,after)
        assert (b,a)==(row['before_copies'],row['after_copies']) and a<=b
        assert a==min([b]+costs)
        sums[group+'_before']+=b;sums[group+'_after']+=a
        n=len(data['instructions'])
        means['before_output'].append(Fraction(b,n+b));means['after_output'].append(Fraction(a,n+a))
        means['before_original'].append(Fraction(b,n));means['after_original'].append(Fraction(a,n))
        if a<b:improved.append(dict(group=group,sha256=key,before=b,after=a))
    assert alloutlets==236
    assert statuses==Counter(report['after_statuses'])==Counter(report['before_statuses'])==Counter(verified=65,proven_infeasible_under_model=19)
    assert outcomes==Counter(report['attempt_outcomes'])==Counter(not_attempted_zero_or_no_incumbent=31,partial_budget=43,completed=10)
    assert sums==Counter(old48_before=10149,old48_after=10147,new36_before=1342,new36_after=1340)
    assert len(improved)==report['improved']==3
    for name,values in means.items():
        period,denom=name.split('_')
        assert abs(float(sum(values)/len(values))-report[f'{period}_success_copy_{denom}_mean'])<1e-14
    boundarypaths=list(D.glob('boundary-*-output.json'))
    assert len(boundarypaths)==report['boundary_complete_outputs']==1
    for path in boundarypaths:
        record=read(path);check(record['input'],record['candidate'])
    assert 'Ran 3 tests' in (D/'boundary-tests.txt').read_text() and '\nOK\n' in (D/'boundary-tests.txt').read_text()
    result=dict(passed=True,reviewed_unix=time.time(),original_inputs=84,legal_incumbents_retained=65,model_certificates_retained=19,
        actual_all_outlets_replayed=236,actual_full_replay_instances=replays,
        before_copies=11491,after_copies=11487,improved=improved,partial_budget_attempts=budgetpartial,
        outcomes=dict(outcomes),root_reviewed_success_only_means={k:float(sum(v)/len(v)) for k,v in means.items()},evidence=evidence,
        scope='All84 unchanged inputs retain original status;65 exact R155/R156 savedincumbents/bests and all236 complete outlets including worse/partial plusboundary replayed with originalidentity/orderedargs/window/hazards. Three proposals save4COPY with no recovery/regression;43 partial searches retain budgetunknown, onlyone contains completed proposal. Total20k/500ms warmstart excludes generating baseline/independentverify, not guaranteed CLI wall. Successful65 means are not all84/full336/officialLevels; no default promotion.')
    (ROOT/'outputs/stage2-root-tree-pair-warmstart-84.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','partial_budget_attempts')}))


if __name__=='__main__':main()
