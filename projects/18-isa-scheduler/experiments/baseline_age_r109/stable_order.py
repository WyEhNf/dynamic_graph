"""Exact stable_fast policy emission without a general ready heap.

Parsed input order is already topological, including register hazards. The
smallest ready index is therefore the next input row. Preserve the same COPY
expiry/last-use rules and bounded failure while avoiding unrelated heap and
last-use-priority maintenance. This is fixed-order emission, not a new search.
"""
from collections import OrderedDict
from time import perf_counter
from .model import BudgetExceeded,InfeasibleSchedule


def emit_stable_order(block,prepared,*,deadline,started,reuse,max_copy_factor=None):
    nodes=block.instructions;count=len(nodes);remaining=list(prepared.remaining)
    positions=[-1]*count;live=OrderedDict();output=[]
    tokens=tuple(f't#{distance}' for distance in range(block.window+1))
    factor=block.window-1 if max_copy_factor is None else max_copy_factor
    if type(factor) is not int or factor<1:raise ValueError('Positive integer COPY factor required')
    limit=max(block.window,factor*max(1,count));prefix=copies=stalled=peak=0
    while prefix<count:
        if perf_counter()>=deadline:raise BudgetExceeded('Incremental scheduling time budget exhausted')
        now=len(output);node=nodes[prefix]
        if live:
            oldest=next(iter(live));age=now-positions[oldest]
            if age>block.window:raise InfeasibleSchedule('Incremental live value expired')
            if age==block.window and not(oldest in prepared.args_unique[prefix] and remaining[oldest]==1):
                output.append({'id':now,'op':'COPY','source':tokens[block.window]})
                positions[oldest]=now;live.move_to_end(oldest);copies+=1;stalled+=1
                if stalled>=block.window or copies>limit:
                    raise InfeasibleSchedule('Incremental heuristic cannot progress; not a global infeasibility proof')
                continue
        row={'id':now,'op':node.op}
        if node.reg is not None:row['reg']=node.reg
        encoded=[tokens[now-positions[source]] for source in node.args]
        if node.op=='COPY':row['source']=encoded[0]
        elif encoded:row['inputs']=encoded
        output.append(row);positions[prefix]=now
        for source in prepared.args_unique[prefix]:
            remaining[source]-=1
            if remaining[source]==0:live.pop(source,None)
        if remaining[prefix]>0:live[prefix]=now
        peak=max(peak,len(live));prefix+=1;stalled=0
    total=sum(row['op']=='COPY' for row in output)
    return {'block_id':block.block_id,'optimized_instructions':output,'stats':{
        'strategy':'stable_fast','original_instruction_count':count,'optimized_instruction_count':len(output),
        'inserted_copy_count':copies,'total_copy_count':total,
        'copy_ratio_output':total/len(output) if output else 0,
        'inserted_copy_ratio_original':copies/count if count else 0,
        'elapsed_ms':(perf_counter()-started)*1000,'bit_width':block.bit_width,
        'max_back_distance':block.window,'original_order':list(range(count)),
        'implementation':'direct_stable_order',
        'incremental':{'max_live_values':peak,'heap_pushes':0,'dependency_edges':sum(len(d) for d in prepared.deps),
                       'rank':'original topological input order','shared_preprocess':reuse,
                       'preprocess_ms':prepared.preprocess_ms,'rank_compute_ms':0,
                       'original_order_peak_live':prepared.original_peak_live}}}
