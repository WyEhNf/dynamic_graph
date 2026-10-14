"""External SERIAL memory oracle; not a contest solver dependency.

Install OR-Tools in research/oracle-env. Integer slots represent order rather
than microseconds: all tasks have one slot, so peak depends only on the order.
Workspace spans [pos,pos+1), output [pos,max(direct_child_pos+1)), or to n for
sinks. AllDifferent positions ensures exactly one Compute in every slot.
Actual serial T=sum(exec_time); single stream introduces zero Events. Thus a
found order has exact contest lifetime semantics. Serial infeasibility does
not imply parallel/deadline infeasibility. No witness or generation field is
read by the model, hint policy, branching strategy or candidate extraction.
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path


def model(case):
    from ortools.sat.python import cp_model
    nodes=case['nodes'];n=len(nodes);index={x['id']:i for i,x in enumerate(nodes)}
    successors=[[] for _ in nodes]
    for i,x in enumerate(nodes):
        for p in x['inputs']:
            successors[index[p]].append(i)
    m=cp_model.CpModel()
    pos=[m.new_int_var(0,n-1,f'p_{i}') for i in range(n)]
    m.add_all_different(pos)
    intervals=[];demands=[]
    for i,x in enumerate(nodes):
        for p in x['inputs']:
            m.add(pos[index[p]]+1<=pos[i])
        if x['workspace_memory']:
            intervals.append(m.new_interval_var(pos[i],1,pos[i]+1,f'w_{i}'))
            demands.append(x['workspace_memory'])
        if x['output_memory']:
            last=m.new_int_var(1,n,f'last_{i}')
            if successors[i]:
                m.add_max_equality(last,[pos[c]+1 for c in successors[i]])
            else:
                m.add(last==n)
            length=m.new_int_var(1,n,f'hold_{i}')
            m.add(length==last-pos[i])
            intervals.append(m.new_interval_var(pos[i],length,last,f'o_{i}'))
            demands.append(x['output_memory'])
    if intervals:
        m.add_cumulative(intervals,demands,case['hardware']['memory_limit'])
    return m,pos


def serial_metrics(nodes,order):
    # Independent count-at-consumer-END recurrence, actual durations.
    idx={x['id']:x for x in nodes};users={i:0 for i in idx}
    for x in nodes:
        for p in x['inputs']:users[p]+=1
    done=set();live=peak=duration=0
    for i in order:
        x=idx[i]
        assert i not in done and all(p in done for p in x['inputs'])
        peak=max(peak,live+x['workspace_memory']+x['output_memory'])
        live+=x['output_memory']
        for p in x['inputs']:
            users[p]-=1
            if not users[p]:live-=idx[p]['output_memory']
        done.add(i);duration+=x['exec_time']
    assert len(done)==len(nodes)
    return duration,peak


def solve(case,seconds=5,workers=1):
    from ortools.sat.python import cp_model
    m,pos=model(case);solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=seconds
    solver.parameters.num_search_workers=workers
    solver.parameters.random_seed=20261011
    start=time.perf_counter();cpu=time.process_time();status=solver.solve(m)
    result=dict(name=case['name'],n=len(case['nodes']),status=solver.status_name(status),
        solve_wall_seconds=time.perf_counter()-start,process_cpu_seconds=time.process_time()-cpu,
        num_branches=solver.num_branches,num_conflicts=solver.num_conflicts,
        limit_seconds=seconds,workers=workers,seed=20261011,
        scope='SERIAL fixed-memory feasibility; UNKNOWN is no proof; not a parallel optimality oracle')
    if status in (cp_model.FEASIBLE,cp_model.OPTIMAL):
        order=[case['nodes'][i]['id'] for i in sorted(range(len(pos)),key=lambda i:solver.value(pos[i]))]
        total,peak=serial_metrics(case['nodes'],order)
        assert peak<=case['hardware']['memory_limit']
        result.update(order=order,T=total,peak_memory=peak,meets_deadline=total<=case['deadline_us'],
            plan=dict(streams=[dict(tasks=[dict(op_id=i,wait_before=[],record_after=-1) for i in order])]))
    return result


def main():
    import ortools
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-n',type=int,default=200);p.add_argument('--seconds',type=float,default=5)
    p.add_argument('--workers',type=int,default=1);p.add_argument('--max-cases',type=int,default=1000000)
    args=p.parse_args();doc=json.loads(args.input.read_text());rows=[];excluded=0
    for case in doc['cases']:
        if len(case['nodes'])>args.max_n or len(rows)>=args.max_cases:
            excluded+=1;continue
        row=solve(case,args.seconds,args.workers);rows.append(row)
        print(case['name'],row['status'],f"{row['solve_wall_seconds']:.3f}s",flush=True)
        # Preserve completed rows after every bounded call, including UNKNOWN.
        evidence=dict(oracle='external serial-slot CP-SAT, not official judge',ortools_version=ortools.__version__,
            python_version=platform.python_version(),input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),arguments=vars(args)|{'input':str(args.input),'output':str(args.output)},
            cases=rows,excluded_by_explicit_scope=excluded)
        args.output.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    if rows:
        evidence['excluded_by_explicit_scope']=excluded
        args.output.write_text(json.dumps(evidence,indent=2),encoding='utf-8')

if __name__=='__main__':main()
