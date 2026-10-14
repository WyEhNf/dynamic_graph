"""Independent Python arbitrary-precision gold values, never solver generated."""
import copy,json
from pathlib import Path
MAX=(1<<63)-1;HUGE=6_000_000_000_000_000_000
def op(i,w,o,inputs=()):return dict(id=i,core_type='AIC',core_num=1,exec_time=1,workspace_memory=w,output_memory=o,inputs=list(inputs))
def flow(*tasks):return dict(tasks=[dict(op_id=i,wait_before=list(wait),record_after=record) for i,wait,record in tasks])
def serial(nodes):return dict(streams=[flow(*[(x['id'],[], -1) for x in nodes])])
def serial_peak(nodes):
    users={x['id']:sum(x['id'] in y['inputs'] for y in nodes) for x in nodes};out={x['id']:x['output_memory'] for x in nodes}
    live=peak=0
    for x in nodes:
        peak=max(peak,live+x['workspace_memory']+x['output_memory']);live+=x['output_memory']
        for p in x['inputs']:
            users[p]-=1
            if not users[p]:live-=out[p]
    return peak
def main():
    cases=[]
    for name,nodes,feasible in [
        ('sum_beyond_max',[op(10,HUGE,HUGE)],False),
        ('peak_exactly_max',[op(10,MAX-1,1)],True),
        ('peak_max_minus_one',[op(10,MAX-2,1)],True),
        ('multiple_parents_over_max',[op(10,0,HUGE),op(20,0,HUGE),op(30,0,0,[10,20])],False),
        ('multiple_parents_exact_max',[op(10,0,MAX//2),op(20,0,MAX//2),op(30,0,1,[10,20])],True),
        ('history_sum_over_max_but_released',[op(10,0,HUGE),op(20,1,0,[10]),op(30,0,HUGE,[20]),op(40,1,0,[30])],True),
        ('affinity_overflow_scale',[op(10,0,HUGE),op(20,0,0,[10]),op(30,0,0,[10])],True),
        ('terminal_sum_over_max',[op(10,0,HUGE),op(20,0,HUGE)],False)]:
        peak=serial_peak(nodes)
        assert (peak<=MAX)==feasible
        cases.append(dict(name=name,hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=MAX,event_record_time=0,event_wait_time=0),nodes=nodes,deadline_us=MAX,expected_feasible=feasible,
            fixed_plan=serial(nodes),gold_valid=feasible,gold_T=len(nodes) if feasible else None,gold_peak=peak,
            big_integer_reason='Python exact original direct-consumer interval allocation; overflow must not wrap/saturate into fits'))
    nodes=[op(10,0,0),op(20,0,0,[10])];plan=dict(streams=[flow((10,[],0)),flow((20,[0],-1))])
    for name,record,wait in [('time_exactly_max',MAX-3,1),('record_add_over_max',MAX,0)]:
        t=1+record+wait+1;valid=t<=MAX
        cases.append(dict(name=name,hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=MAX,event_record_time=record,event_wait_time=wait),nodes=nodes,deadline_us=MAX,expected_feasible=True,fixed_plan=plan,gold_valid=valid,gold_T=t,gold_peak=0,
            big_integer_reason='Exact1+Record+Wait+Compute; graph has feasible event-free serial alternative'))
    nodes=[op(10,0,0),op(20,0,0),op(30,0,0,[10,20])];wait=MAX//2+1
    plan=dict(streams=[flow((10,[],0)),flow((20,[],1)),flow((30,[0,1],-1))])
    cases.append(dict(name='wait_product_over_max',hardware=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=MAX,event_record_time=0,event_wait_time=wait),nodes=nodes,deadline_us=MAX,expected_feasible=True,fixed_plan=plan,gold_valid=False,gold_T=1+2*wait+1,gold_peak=0,
        big_integer_reason='Two unique waits: exact product exceedsMAX; serial graph alternative feasible'))
    base=Path('research/batch42');base.mkdir(parents=True,exist_ok=True)
    local=copy.deepcopy(cases)
    for c in local:
        c['gold_T']=str(c['gold_T']) if c['gold_T'] is not None else None
        c['gold_peak']=str(c['gold_peak'])
    Path('data/numeric-controls-batch42.json').write_text(json.dumps(dict(format='aicore-local-v1',cases=local)),encoding='utf-8')
    Path('reports/numeric-gold-batch42.json').write_text(json.dumps(dict(maximum=MAX,cases=cases,affinity_exact=HUGE*1024//2,note='Integers may exceed64 bits here; do not load gold fields into signed64 parser. Fixed-plan gold and graph feasibility are distinct.')),encoding='utf-8')
    print(len(cases),'independent bigint numeric controls')
if __name__=='__main__':main()
