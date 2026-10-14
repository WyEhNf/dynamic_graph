"""Root original-set liveness, exhaustive cut orders and full-plan review."""
import itertools
import json
import sys
import time
from collections import Counter
from review_stage2_observer_r52 import ROOT,P,sha,simulate

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main(corrected=False):
    d=P/'research/batch53';reports=P/'reports';plan=read(d/'execution-plan.json')
    for row in plan['files']:assert sha(P/row['path'])==row['sha256']
    gold=read(d/'corrected/gold.json' if corrected else P/'data/final-live-gold-batch53.json')['cases'];assert len(gold)==176
    if corrected:
        checkpoint=read(d/'small-acceptance-checkpoint.json')
        for row in checkpoint['files']:assert sha(P/row['path'])==row['sha256']
        revision=read(d/'corrected/revision-map.json');assert len(revision['changes'])==7
        original=read(P/'data/final-live-gold-batch53.json')['cases'];changes={r['name']:r for r in revision['changes']}
        for oldcase,newcase in zip(original,gold):
            for name in ('name','group','hardware','nodes','deadline_us'):assert oldcase[name]==newcase[name]
            if oldcase['name'] in changes:
                assert oldcase['prefix']==changes[oldcase['name']]['before_prefix'] and newcase['prefix']==changes[oldcase['name']]['after_prefix']
            else:assert oldcase==newcase
    spec=read(d/'gold-declaration.json');assert dict(Counter(c['group'] for c in gold))==spec['planned_control_counts']
    qualification_failures=[]
    for c in gold:
        if c['group']!='fixed_seed_small_dags':continue
        D=set(c['prefix']);nodes={n['id']:n for n in c['nodes']}
        for r in c['requests']:
            p=r['producer'];remaining={n['id'] for n in c['nodes'] if p in n['inputs']}-D
            if p not in D or not nodes[p]['output_memory'] or not remaining:
                qualification_failures.append(dict(name=c['name'],producer=p,reason='random held producer eligibility absent'))
    executions=read(d/('corrected/execution-status.json' if corrected else 'execution-status.json'))['statuses'];assert executions and all(r['actual_exit_code']==0 for r in executions)
    suffix='-corrected' if corrected else ''
    actuals=[read(reports/f'final-live-{role}{suffix}-batch53.json')['cases'] for role in ('gcc','ubsan')]
    for rows in actuals:assert len(rows)==176
    requests=orders=whole=legal=pruned=budgets=0
    for index,c in enumerate(gold):
        nodes={n['id']:n for n in c['nodes']};users={i:set() for i in nodes}
        for i,n in nodes.items():
            assert len(n['inputs'])==len(set(n['inputs']))
            for p in n['inputs']:users[p].add(i)
        def held(done):return sum(n['output_memory'] for i,n in nodes.items() if i in done and (not users[i] or users[i]-done))
        def execute(order,initial):
            done=set(initial);peak=held(done)
            for i in order:
                assert i not in done and set(nodes[i]['inputs'])<=done
                peak=max(peak,held(done)+nodes[i]['workspace_memory']+nodes[i]['output_memory']);done.add(i)
            return peak,held(done)
        D=set(c['prefix']);assert execute(c['prefix'],set())[0]<=c['hardware']['memory_limit']
        for role_rows in actuals:assert role_rows[index]['name']==c['name'] and len(role_rows[index]['requests'])==len(c['requests'])
        for j,r in enumerate(c['requests']):
            p=r['producer'];C=set();stack=list(users[p]-D)
            while stack:
                v=stack.pop()
                if v in D or v in C:continue
                C.add(v);stack.extend(nodes[v]['inputs'])
            eligible=p in D and nodes[p]['output_memory']>0 and bool(users[p]-D)
            expected=r['candidate_gold'];bound=r['bound_gold'];requests+=1
            if bound is not None:
                assert eligible and len(C)<=128
                F=held(D|C)
                released=sum(nodes[v]['output_memory'] for v in D if users[v] and users[v]-D and users[v]-D<=C)
                born=sum(nodes[v]['output_memory'] for v in C if not users[v] or users[v]-(D|C))
                assert F==held(D)-released+born==int(bound['final'])==(bound['hi']<<64)+bound['lo']
                assert sum(amount for _,amount in bound['events'])==bound['work']
                if len(nodes)<=8:
                    bank={tuple(x['order']):x for e in c['enumeration'] if e['producer']==p for x in e['orders']}
                    for order in itertools.permutations(sorted(C)):
                        done=set(D);valid=True
                        for v in order:
                            if not set(nodes[v]['inputs'])<=done:valid=False;break
                            done.add(v)
                        if not valid:continue
                        stored=bank.pop(order);peak,final=execute(order,D)
                        assert peak==stored['peak'] and final==F==stored['final_live'];orders+=1
                    assert not bank
            if expected['valid']:
                assert set(expected['order'])==C
                peak,final=execute(expected['order'],D)
                assert peak==expected['peak']<=c['hardware']['memory_limit'] and final==expected['final_live']==int(bound['final'])
            if expected['pruned']:
                source=c['requests'][r['incumbent_source']]['candidate_gold']
                assert source['valid'] and int(r['incumbent_final'])==source['final_live']<int(bound['final'])
                assert not expected['valid'];pruned+=1
            for role_rows in actuals:
                actual=role_rows[index]['requests'][j];assert actual['producer']==p
                for k in ('valid','exhausted','pruned','work','peak','final_live','pending','order'):assert actual[k]==expected[k]
                if actual['bound'] is not None:
                    a=actual['bound'];assert a['hi']==bound['hi'] and a['lo']==bound['lo'] and a['work']==bound['work']
                    inc=int(r['incumbent_final']) if r['incumbent_final'] is not None else expected['final_live']
                    assert a['dominated']==(int(bound['final'])>inc)
            fixed=c['full_plans'][j];order=[t['op_id'] for t in fixed['fixed_plan']['streams'][0]['tasks']]
            assert len(order)==len(nodes) and set(order)==set(nodes)
            peak,_=execute(order,set());assert peak==int(fixed['gold_peak']) and len(nodes)==int(fixed['gold_T'])
            valid=peak<=c['hardware']['memory_limit'];assert valid==fixed['gold_valid'];whole+=1;legal+=valid
        if c['bound_budget'] is not None:
            budgets+=1;b=c['bound_budget'];r=c['requests'][b['request']]
            work=0;completed=True
            for _,amount in r['bound_gold']['events']:
                if amount>b['limit']-work:work=b['limit'];completed=False;break
                work+=amount
            assert work==b['work'] and completed==b['complete']
            for role_rows in actuals:assert role_rows[index]['requests'][b['request']]['budget']==dict(complete=completed,work=work)
    assert (requests,orders,whole,legal,budgets,pruned)==(347,558 if corrected else 550,347,311,32,87)
    numeric=read(reports/f'final-live-fixed-ubsan{suffix}-batch53.json');assert numeric['total']==numeric['passed']==347
    fixed=read(d/'corrected/fixed-gold.json' if corrected else P/'data/final-live-fixed-gold-batch53.json')['cases']
    assert len(fixed)==347
    for case,record in zip(fixed,numeric['cases']):
        unbounded=dict(case,hardware=dict(case['hardware'],memory_limit=1<<100))
        T,peak=simulate(unbounded,case['fixed_plan']);valid=peak<=case['hardware']['memory_limit']
        assert T==int(case['gold_T']) and peak==int(case['gold_peak']) and valid==case['gold_valid']==record['valid']
    original=read(d/'../batch52/observer-selected12-input-only.json')['cases']
    before=read(reports/'observer-baseline-batch52.json')['cases'];after=read(reports/'final-live-selected12-batch53.json')['cases']
    comparison=[];plans=0
    for data,b,a in zip(original,before,after):
        assert data['name']==b['name']==a['name']
        w=a['whole'];assert a['helper']['work']<=16000000
        if w['valid']:
            T,peak=simulate(data,w['plan']);assert T==w['T'] and peak==w['peak'];plans+=1
        comparison.append(dict(name=a['name'],before=b['whole']['valid'],after=w['valid'],
            old_work=b['helper']['work'],new_work=a['helper']['work'],whole_plan_equal=b['whole']['plan']==w['plan']))
    summary=read(reports/'final-live-summary-batch53.json')
    assert sum(x['before'] for x in comparison)==summary['old_selected12_success']
    assert sum(x['after'] for x in comparison)==summary['new_selected12_success']
    result=dict(passed=not qualification_failures,physical_and_numeric_replay_passed=True,qualification_failures=qualification_failures,
        reviewed_unix=time.time(),execution_plan_sha256=sha(d/'execution-plan.json'),
        original_gold_cases=176,probe_requests=347,independently_enumerated_cut_orders=orders,
        full_original_physical_plans=347,legal_fixed_plans=311,expected_invalid_fixed_plans=36,
        GCC_and_UBSan_control_checks=352,strict_dominance_controls=87,independent_budget_boundaries=32,
        selected12_actual_legal_plans=plans,comparison=comparison,
        recovered=summary['recovered'],lost=summary['lost'],scope='Initial physical/numeric results matched on176/347/550/87/32 controls, but seven random fixtures violate predeclared eligible held-producer condition: complete176 acceptance FAILED. Same R52 12 functionals unchanged. Preserve all initial inputs/results; fixture-only revision required, no default promotion.')
    if corrected:
        assert not qualification_failures
        result.update(initial_qualification_failed=7,corrected_prefixes=7,qualified_random_controls=64,
            corrected_checkpoint_sha256=sha(d/'small-acceptance-checkpoint.json'),revision_map_sha256=sha(d/'corrected/revision-map.json'),
            scope='Corrected176 controls: same original graphs/hardware/deadlines/seed and only7 fixture prefixes changed; all64 random held-producer prerequisites satisfied.347 H(D union C) and complete original plans/558 exact cutorders/87strict prunes/32 charged boundaries independently reviewed; actual reused GCC/UBSan EXEs agree. Initial7qualification failures preserved. Same12 actual plans/work verified0recoveries/0loss. No full63/250/1099/default/performance or universal proof.')
    target=ROOT/'outputs/stage2-root-final-live-r53.json'
    history=ROOT/'outputs/stage2-root-final-live-initial-physics-r53.json'
    if not corrected and target.exists() and not history.exists():history.write_bytes(target.read_bytes())
    target.write_text(json.dumps(result,indent=2)+'\n')
    if not corrected:(ROOT/'outputs/stage2-root-final-live-initial-r53.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='comparison'}))

if __name__=='__main__':main('--corrected' in sys.argv)
