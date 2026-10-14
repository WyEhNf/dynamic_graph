"""Independent Python bigint original-DAG serial physics, not solver logic."""
import copy
import itertools
import json
from pathlib import Path


def replay(case,order):
    nodes={node['id']:node for node in case['nodes']}
    users={i:sum(i in node['inputs'] for node in nodes.values()) for i in nodes}
    done=set();live=peak=now=0;trace=[]
    assert len(order)==len(nodes)==len(set(order)) and set(order)==set(nodes)
    for i in order:
        node=nodes[i];assert set(node['inputs'])<=done
        assert 1<=node['core_num']<=case['hardware']['aic_core_num']
        allocation=live+node['workspace_memory']+node['output_memory']
        peak=max(peak,allocation)
        trace.append(dict(phase='BEGIN',id=i,time=now,live_before=live,workspace=node['workspace_memory'],output=node['output_memory'],allocation=allocation))
        live+=node['output_memory'];now+=node['exec_time'];done.add(i)
        freed=[]
        for parent in node['inputs']:
            users[parent]-=1
            if users[parent]==0:live-=nodes[parent]['output_memory'];freed.append(parent)
        trace.append(dict(phase='END_before_global_sink_cleanup',id=i,time=now,live=live,freed_original_direct_parents=freed))
    assert live==sum(node['output_memory'] for i,node in nodes.items() if users[i]==0 and not any(i in other['inputs'] for other in nodes.values()))
    return dict(valid=peak<=case['hardware']['memory_limit'] and now<=case['deadline_us'],T=now,peak=peak,trace=trace,live_before_global_T_cleanup=live,live_after_global_T_cleanup=0)


def main():
    original=json.loads(Path('research/batch52/hand-frontier-counterexample.json').read_text())['cases'][0]
    controls=[];profiles=[]
    for label,cap in [('cap100',100),('cap120_greedy_success',120),('cap99_infeasible_lowerbound',99),('exactMAX',2**63-1)]:
        case=copy.deepcopy({key:original[key] for key in ('hardware','nodes','deadline_us')})
        case['hardware']['memory_limit']=cap
        if label=='exactMAX':
            unit=(2**63-1)//100;remainder=(2**63-1)-100*unit
            for node in case['nodes']:
                node['workspace_memory']*=unit;node['output_memory']*=unit
            case['nodes'][2]['workspace_memory']+=remainder
        for role,order in [('alternative',[103,99,17]),('greedy',[103,17,99])]:
            name=f'{label}_{role}';gold=replay(case,order)
            control=copy.deepcopy(case);control['name']=name
            control['fixed_plan']=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in order])])
            control.update(gold_valid=gold['valid'],gold_T=str(gold['T']),gold_peak=str(gold['peak']))
            controls.append(control);profiles.append(dict(name=name,order=order,**gold))
    assert [c['gold_valid'] for c in controls]==[True,False,True,True,False,False,True,False]
    assert profiles[0]['peak']==100 and profiles[2]['peak']==100 and profiles[3]['peak']==120 and profiles[6]['peak']==2**63-1
    # Exhaust all original-DAG topological orders for the 3-node control.
    opt=min(replay(original,list(order))['peak'] for order in itertools.permutations((103,17,99)) if order[0]==103)
    assert opt==100
    Path('research/batch52/whole-fixed-gold.json').write_text(json.dumps(dict(format='aicore-local-fixed-plan-bigint-v1',cases=controls),indent=2)+'\n',encoding='utf-8')
    Path('reports/whole-python-gold-batch52.json').write_text(json.dumps(dict(status='Independent whole-original-DAG Python bigint gold executed',controls=8,valid=4,invalid=4,optimum_cap100=opt,cap120='Greedy order succeeds withpeak120;alternative100;graph feasible',default_failure_claim=False,profiles=profiles),indent=2)+'\n',encoding='utf-8')
    print('8 independent complete-plan bigint controls;cap100 optimum100;cap120 greedy success',flush=True)


if __name__=='__main__':main()
