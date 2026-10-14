"""Explicit same-incumbent region wrapper; ordinary/default entry untouched."""
from collections import Counter
from time import perf_counter
from .general_region_anytime import RegionStop, _prepare, search_general_region


def refine_general_regions(data, incumbent, *, time_budget_ms=500, max_states=20000,
        max_transitions=20000, max_outcomes=16, region_nodes=32, max_regions=64,
        on_completed=None):
    started=perf_counter(); deadline=started+time_budget_ms/1000
    if min(time_budget_ms,max_states,max_transitions,max_outcomes,region_nodes,max_regions)<=0:
        raise ValueError('Positive budgets required')
    if region_nodes>32 or max_regions>64: raise ValueError('Fixed research region caps exceeded')
    best={'output':incumbent['output'],'original_order':incumbent['original_order'],
          'copies':sum(row['op']=='COPY' for row in incumbent['output']['optimized_instructions'])}
    attempts=[]; diagnostics=[]; processed=transitions=complete=0; eligible=[]; capped=[]
    outcome='completed'; layout=None
    def check():
        if perf_counter()>=deadline: raise RegionStop('total_deadline')
    def sink(start,candidate):
        nonlocal best,complete
        complete+=1
        if candidate['copies']<best['copies']: best=candidate
        if on_completed is not None: on_completed(start,candidate)
    try:
        graph=_prepare(data,incumbent,check); graph['raw_data']=data; graph['incumbent']=incumbent
        layout=graph['layout']; n=graph['n']; by_cursor=Counter(); cursor=0
        for row in incumbent['output']['optimized_instructions']:
            check()
            if row['op']=='COPY': by_cursor[cursor]+=1
            else: cursor+=1
        starts=set()
        for rank in by_cursor:
            check(); grid=(rank//16)*16
            for anchor in (grid,grid-16): starts.add(min(max(0,anchor),max(0,n-region_nodes)))
        all_regions=[]
        for start in starts:
            check(); count=sum(value for rank,value in by_cursor.items() if start<=rank<min(n,start+region_nodes))
            all_regions.append((start,count))
        all_regions.sort(key=lambda item:(-item[1],item[0])); eligible=all_regions[:max_regions]
        for start,local_copies in eligible:
            check()
            if processed>=max_states: raise RegionStop('state_budget')
            if transitions>=max_transitions: raise RegionStop('transition_budget')
            result=search_general_region(data,incumbent,start,region_nodes=region_nodes,
                time_budget_ms=max(1e-9,(deadline-perf_counter())*1000),absolute_deadline=deadline,
                max_states=max_states-processed,max_transitions=max_transitions-transitions,
                max_outcomes=max_outcomes,prepared=graph,on_completed=lambda candidate:sink(start,candidate))
            stats=result['stats']; processed+=stats['processed_states']; transitions+=stats['attempted_transitions']
            attempts.append({'start':start,'initial_local_copies':local_copies,'stats':stats,
                             'diagnostic_reference':len(diagnostics)})
            diagnostics.append(result['diagnostics'])
            if stats['outcome']=='partial_outlet_limit': capped.append(start); outcome='partial_outlet_limit'; continue
            if stats['outcome']!='exhausted_improvement_search': outcome=stats['outcome']; break
    except RegionStop as error: outcome='partial_'+str(error)
    return {'best':best,'diagnostics':diagnostics,'stats':{'outcome':outcome,
        'processed_states':processed,'attempted_transitions':transitions,'complete_outputs':complete,
        'attempts':attempts,'eligible_regions':eligible,'outlet_limited_regions':capped,'resource_layout':layout,
        'search_emit_ms':(perf_counter()-started)*1000,
        'parameters':{'total_ms':time_budget_ms,'expansions':max_states,'transition_attempts':max_transitions,
                      'outlets_each_region':max_outcomes,'region_nodes':region_nodes,'max_regions':max_regions},
        'scope':'All proposals share initial incumbent. Diagnostic export after literal search deadline. No default hook.'}}
