"""Adopt an improving complete schedule immediately and rebuild neighborhoods.

All iterations share one wall/work budget. A saved complete improvement can be
used as the next incumbent; unfinished search states remain only as diagnostics
against their own incumbent. There is no global optimality/infeasibility claim.
"""
from time import perf_counter

from .balanced_mobile_fast_refine import select_balanced_regions
from .general_region_anytime import RegionStop
from .mobile_backbone_bound import prepare_mobile, search_mobile_backbone


def refine_online_bound_mobile(data, incumbent, *, time_budget_ms=500,
        max_states=20000, max_transitions=20000, max_outcomes=4,
        max_regions=64, max_rounds=8, on_completed=None, resource_snapshot=None):
    if min(time_budget_ms,max_states,max_transitions,max_outcomes,max_regions,max_rounds)<=0:
        raise ValueError('Positive budgets required')
    if max_states>20000 or max_transitions>20000 or max_regions>64:
        raise ValueError('At most 20000 work units and 64 regions')
    started=perf_counter();deadline=started+time_budget_ms/1000
    best=dict(incumbent)
    best['copies']=sum(row['op']=='COPY' for row in best['output']['optimized_instructions'])
    diagnostics=[];attempts=[];rounds=[];processed=transitions=complete=regions=0
    outcome='completed'

    def check():
        if perf_counter()>=deadline:raise RegionStop('total_deadline')
        if processed>=max_states:raise RegionStop('state_budget')
        if transitions>=max_transitions:raise RegionStop('transition_budget')
        if regions>=max_regions:raise RegionStop('region_budget')

    try:
        for round_index in range(max_rounds):
            check()
            initial=best
            if not best['copies']:
                outcome='zero_copy_lower_bound';break
            graph=prepare_mobile(data,initial,check)
            if resource_snapshot is not None:
                snapshot=resource_snapshot()
                need=graph['layout']['diagnostic_bound_bytes']+(max_rounds+1)*graph['layout']['complete_proposal_bound_bytes']
                if snapshot['disk_free_bytes']<512*1024**2+need:raise RegionStop('resource_preflight')
            selected,selected_count=select_balanced_regions(graph,initial,check,max_regions)
            round_stats={'round':round_index,'before_copies':initial['copies'],
                'neighborhood_count':selected_count,'first_region':regions}
            rounds.append(round_stats)
            for item in selected:
                check()
                region_index=regions
                remaining_ms=(deadline-perf_counter())*1000
                local_ms=min(max(100,min(250,item['span']/20)),remaining_ms)
                local_work=max(2000,min(10000,2*item['span']+128))

                def sink(candidate):
                    nonlocal best,complete
                    complete+=1
                    improved=candidate['copies']<best['copies']
                    if improved:best=candidate
                    if on_completed is not None:on_completed(region_index,candidate)
                    if resource_snapshot is not None and resource_snapshot()['disk_free_bytes']<512*1024**2:
                        raise RegionStop('producer_resource_reserve')
                    if improved:
                        # The engine retains this completed candidate before
                        # the callback stops further work in the old state.
                        raise RegionStop('reseed_after_improvement')

                result=search_mobile_backbone(data,initial,item['region'],
                    time_budget_ms=local_ms,absolute_deadline=deadline,
                    max_states=min(local_work,max_states-processed),
                    max_transitions=min(local_work,max_transitions-transitions),
                    max_outcomes=max_outcomes,prepared=graph,on_completed=sink)
                stats=result['stats'];processed+=stats['processed_states'];transitions+=stats['attempted_transitions']
                diagnostic=result['diagnostics']
                diagnostic.incumbent=initial
                diagnostics.append(diagnostic)
                attempts.append(dict(item,round=round_index,region_index=region_index,stats=stats))
                regions+=1
                if stats['outcome'].startswith('partial_producer_resource'):
                    raise RegionStop('producer_resource_reserve')
                if best['copies']<initial['copies']:break
            round_stats.update(after_copies=best['copies'],end_region=regions,
                               adopted=best['copies']<initial['copies'])
            if best['copies']>=initial['copies']:break
        else:
            outcome='partial_round_budget'
    except RegionStop as error:
        outcome='partial_'+str(error)
    return {'best':best,'diagnostics':diagnostics,'stats':{'outcome':outcome,
        'processed_states':processed,'attempted_transitions':transitions,
        'complete_outputs':complete,'attempts':attempts,'rounds':rounds,
        'search_emit_ms':(perf_counter()-started)*1000,
        'parameters':{'time_budget_ms':time_budget_ms,'max_states':max_states,
            'max_transitions':max_transitions,'max_regions':max_regions,'max_rounds':max_rounds,
            'max_outcomes':max_outcomes,'region_work':'max(2000,min(10000,2*span+128))',
            'region_ms':'max(100,min(250,span/20))'},
        'scope':'One shared budget, first complete improvement re-seeds neighborhoods; every frontier identifies its own incumbent.'}}
