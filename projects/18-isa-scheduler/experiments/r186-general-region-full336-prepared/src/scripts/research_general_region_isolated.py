"""Prepare R184 only until reviewed. Explicit --run is the fixed 81-input R185.

No old corpus/baseline/default execution. OSError preserves partial evidence.
"""
import argparse
import ast
from collections import Counter
import ctypes
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from isa_scheduler.general_region_refine import refine_general_regions
from isa_scheduler.general_region_anytime import iter_region_frontier
from isa_scheduler.verify import verify, interpret, IntegerSemantics
from scripts.raw_general_region_oracle import solve_raw
from scripts.general_region_raw_checks import construct_initial,replay,replay_label

SOURCE=ROOT/'experiments/r183-general-region-reserve-prepared'
PREPARED=ROOT/'experiments/r184-general-region-functional-prepared'
RESULTS=ROOT/'experiments/r185-general-region-functional'
RESERVE=512*1024**2


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprint(data): return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def lines(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream: yield json.loads(line)
def write(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def payload(value): return json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n'


def resources():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('page_faults',ctypes.c_ulong)]+[(key,ctypes.c_size_t) for key in (
            'peak_working_set','working_set','peak_paged_pool','paged_pool','peak_nonpaged_pool','nonpaged_pool','pagefile','peak_pagefile')]
    counters=Counters(); counters.cb=ctypes.sizeof(counters)
    kernel=ctypes.windll.kernel32; kernel.GetCurrentProcess.restype=ctypes.c_void_p
    api=ctypes.windll.psapi.GetProcessMemoryInfo; api.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
    if not api(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb): raise OSError('RSS read failed')
    return {'disk_free_bytes':shutil.disk_usage(ROOT).free,'working_set_bytes':counters.working_set,
            'process_peak_working_set_bytes':counters.peak_working_set,
            'scope':'Current-input sampled RSS; OS peak is process lifetime, not isolated per-input peak.'}


def four_check(data,candidate):
    observed=replay(data,candidate['output'],candidate['original_order'])
    if observed['copies']!=candidate['copies']: raise AssertionError('COPY statistic disagrees with raw rows')
    verify(data,candidate['output'])
    registers=sorted({row['reg'] for row in data['instructions'] if 'reg' in row})
    for seed in (18501,18502):
        initial={reg:seed-29*i for i,reg in enumerate(registers)}
        for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
            if interpret(data['instructions'],initial,semantics)!=interpret(candidate['output']['optimized_instructions'],initial,semantics):
                raise AssertionError('Independent local integer replay failed')
    return {'raw_identity_order_hazard':True,'symbolic':True,'integer_models':['8signed','16unsigned','32signed'],
            'integer_initial_seeds':[18501,18502],'copies':observed['copies'],'local_semantics_not_official':True}


def prepare():
    PREPARED.mkdir(exist_ok=False)
    frozen=read(SOURCE/'source-provenance.json')
    for item in frozen['source_files']:
        if sha(ROOT/item['path'])!=item['sha256']: raise AssertionError('R183 source changed: '+item['path'])
    shutil.copyfile(SOURCE/'inputs.jsonl',PREPARED/'raw80.jsonl')
    shutil.copyfile(ROOT/'research/level-stage/general-region-hand11.json',PREPARED/'hand11.json')
    cases=[{'kind':'tiny_frozen','input':data} for data in lines(PREPARED/'raw80.jsonl')]
    hand=read(PREPARED/'hand11.json'); cases.append({'kind':'hand11','input':hand['input']})
    assert len(cases)==81 and len({fingerprint(case['input']) for case in cases})==81
    (PREPARED/'cases.jsonl').write_text(''.join(payload(case) for case in cases),encoding='utf-8')
    paths=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'scripts/general_region_raw_checks.py',
        ROOT/'scripts/raw_general_region_oracle.py',ROOT/'tests/test_general_region_contracts.py',
        ROOT/'research/level-stage/general-region-functional-runner.md']
    entries={}
    for path in paths:
        relative=str(path.relative_to(ROOT)); target=PREPARED/'src'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target); entries[relative]=sha(path)
        if path.suffix=='.py': ast.parse(path.read_text(encoding='utf-8'),filename=relative)
    manifest={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':entries,
        'source_aggregate_sha256':hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest(),
        'prepared_sha256':{name:sha(PREPARED/name) for name in ('raw80.jsonl','hand11.json','cases.jsonl')},
        'frozen_R183_manifest_sha256':sha(SOURCE/'source-provenance.json'),
        'count':81,'parameters':{'search_ms':500,'search_expansions':20000,'search_transitions':20000,
        'regions':64,'region_size':32,'outlets_each_region':16,'reserve_bytes':RESERVE,
        'raw_oracle_ms':500,'raw_oracle_expansions':20000,'raw_oracle_discovered':20000,
        'initial_construct_ms':500,'initial_construct_states':20000},
        'phase':'Prepared only; no solver/oracle/verification/contracts executed.'}
    write(PREPARED/'source-provenance.json',manifest)
    print(json.dumps({'prepared':str(PREPARED),'count':81,'source_sha256':manifest['source_aggregate_sha256'],'solver_executed':False}))


def export_and_replay(data,initial,result,key,folder):
    tick=perf_counter(); snapshots=result.pop('diagnostics'); exports=[]
    for index,snapshot in enumerate(snapshots):
        start=result['stats']['attempts'][index]['start']; target=folder/f'{key[:16]}-region{index}-frontier.jsonl'
        labels={}; counts=Counter(); materialize=jsonio=rawcheck=0.0; total_bytes=0
        with target.open('w',encoding='utf-8',newline='\n') as stream:
            iterator=iter(iter_region_frontier(snapshot))
            while True:
                clock=perf_counter()
                try: row=next(iterator)
                except StopIteration: materialize+=perf_counter()-clock; break
                materialize+=perf_counter()-clock; counts[row['kind']]+=1
                clock=perf_counter(); encoded=payload(row); size=len(encoded.encode('utf-8'))
                limit=2048 if row['kind'] in ('open','unfinished_expansion') else 1024
                if size>limit: raise AssertionError('Actual serialized record exceeds frozen byte bound')
                stream.write(encoded); total_bytes+=size; jsonio+=perf_counter()-clock
                clock=perf_counter()
                if row['kind']=='immutable_label':
                    labels[row['label_version']]=row; replay_label(data,initial,start,labels,row)
                elif row['kind'] in ('open','unfinished_expansion'): replay_label(data,initial,start,labels,row)
                rawcheck+=perf_counter()-clock
        exports.append({'start':start,'path':str(target.relative_to(ROOT)),'sha256':sha(target),'counts':dict(counts),
            'bytes':total_bytes,'materialization_seconds':materialize,'jsonio_seconds':jsonio,'raw_replay_seconds':rawcheck})
        snapshots[index]=None; del snapshot,labels
    snapshots.clear()
    return exports,perf_counter()-tick


def run():
    manifest=read(PREPARED/'source-provenance.json')
    for relative,expected in manifest['source_sha256'].items():
        if sha(ROOT/relative)!=expected: raise AssertionError('Frozen source changed: '+relative)
    for name,expected in manifest['prepared_sha256'].items():
        if sha(PREPARED/name)!=expected: raise AssertionError('Frozen input changed: '+name)
    RESULTS.mkdir(exist_ok=False); shutil.copyfile(PREPARED/'source-provenance.json',RESULTS/'source-provenance.json')
    records=[]; started=perf_counter(); current_key=None
    try:
        for case in lines(PREPARED/'cases.jsonl'):
            data=case['input']; key=fingerprint(data); current_key=key; tick=perf_counter(); before_resource=resources()
            if before_resource['disk_free_bytes']<RESERVE:
                record={'sha256':key,'kind':case['kind'],'status':'resource_unknown','reason':'before_initial_below_reserve'}
                records.append(record); write(RESULTS/'partial-records.json',records); continue
            clock=perf_counter()
            if case['kind']=='hand11': construction={'outcome':'saved_hand_initial','candidate':read(PREPARED/'hand11.json')['baseline']}
            else: construction=construct_initial(data,max_states=20000,time_budget_ms=500)
            initial_seconds=perf_counter()-clock; initial=construction.get('candidate'); checks=0; verify_seconds=0.0
            if initial is not None:
                clock=perf_counter(); four_check(data,initial); verify_seconds+=perf_counter()-clock; checks+=1
                write(RESULTS/f'{key[:16]}-initial.json',dict(initial,input_sha256=key))
            clock=perf_counter(); oracle=solve_raw(data,max_states=20000,max_discovered=20000,time_budget_ms=500) if case['kind']=='tiny_frozen' else {'outcome':'not_applicable_N11'}
            oracle_seconds=perf_counter()-clock
            if oracle.get('output') is not None:
                gold={'output':oracle['output'],'original_order':oracle['original_order'],'copies':oracle['copies']}
                clock=perf_counter(); four_check(data,gold); verify_seconds+=perf_counter()-clock; checks+=1
            write(RESULTS/f'{key[:16]}-oracle.json',oracle)
            if initial is not None and oracle['outcome']=='closed_infeasible': raise AssertionError('Initial contradicts raw oracle proof')
            complete_path=RESULTS/f'{key[:16]}-complete.jsonl'; sink_seconds=0.0; sink_bytes=0; sink_count=0; resource_samples=[before_resource]
            result=None; exports=[]; export_seconds=0.0; search_seconds=0.0
            if initial is not None:
                with complete_path.open('w',encoding='utf-8',newline='\n') as stream:
                    def sink(region,candidate):
                        nonlocal sink_seconds,sink_bytes,sink_count
                        clock=perf_counter(); encoded=payload({'input_sha256':key,'region_start':region,'candidate':candidate})
                        stream.write(encoded); stream.flush(); sink_bytes+=len(encoded.encode('utf-8')); sink_count+=1
                        sink_seconds+=perf_counter()-clock; resource_samples.append(resources())
                    clock=perf_counter(); result=refine_general_regions(data,initial,on_completed=sink,resource_snapshot=resources)
                    search_seconds=perf_counter()-clock
                clock=perf_counter()
                for saved in lines(complete_path):
                    candidate=saved['candidate']; four_check(data,candidate); checks+=1
                    if oracle['outcome']=='optimal' and candidate['copies']<oracle['copies']: raise AssertionError('Candidate contradicts broad raw optimum')
                verify_seconds+=perf_counter()-clock
                exports,export_seconds=export_and_replay(data,initial,result,key,RESULTS)
                clock=perf_counter(); four_check(data,result['best']); verify_seconds+=perf_counter()-clock; checks+=1
                write(RESULTS/f'{key[:16]}-best.json',dict(result['best'],input_sha256=key))
            after_resource=resources(); resource_samples.append(after_resource)
            record={'sha256':key,'kind':case['kind'],'node_count':len(data['instructions']),'bit_width':data['bit_width'],
                'status':'verified_initial_fallback' if result is not None else 'no_initial_unknown',
                'construction':{k:v for k,v in construction.items() if k!='candidate'},'oracle_outcome':oracle['outcome'],
                'oracle_copies':oracle.get('copies'),'before_copies':None if initial is None else initial['copies'],
                'after_copies':None if result is None else result['best']['copies'],'stats':None if result is None else result['stats'],
                'actual_complete_outputs':sink_count,'actual_complete_bytes':sink_bytes,'four_checked_outputs':checks,
                'diagnostic_exports':exports,'resources':{'before':before_resource,'after':after_resource,
                    'sampled_working_set_max_bytes':max(sample['working_set_bytes'] for sample in resource_samples),
                    'process_lifetime_peak_working_set_bytes':after_resource['process_peak_working_set_bytes']},
                'timing_seconds':{'initial_construct':initial_seconds,'raw_oracle':oracle_seconds,'search_including_sink':search_seconds,
                    'sink_jsonio':sink_seconds,'four_verify':verify_seconds,'diagnostic_export_and_raw_replay':export_seconds,
                    'whole_input':perf_counter()-tick},'scope':'All81 denominator retained; local models, not official Level.'}
            records.append(record); write(RESULTS/'partial-records.json',records)
            print(json.dumps({'sha256':key,'status':record['status'],'oracle':oracle['outcome'],'before':record['before_copies'],
                'after':record['after_copies'],'complete':sink_count}),flush=True)
        report={'count':len(records),'records':records,'elapsed_seconds':perf_counter()-started,
            'statuses':dict(Counter(r['status'] for r in records)),'oracle_statuses':dict(Counter(r.get('oracle_outcome') for r in records)),
            'actual_complete_outputs':sum(r.get('actual_complete_outputs',0) for r in records),
            'scope':'Fixed80 tiny +hand11 isolated functionality; no oldbaseline/oracle/default/full336 rerun. Unknown retained; not official Level.'}
        write(RESULTS/'report.json',report)
    except BaseException as error:
        write(RESULTS/'failure.json',{'input_sha256':current_key,'type':type(error).__name__,'message':str(error),
            'completed_records':len(records),'elapsed_seconds':perf_counter()-started,'automatic_restart':False})
        raise
    evidence={str(path.relative_to(RESULTS)):sha(path) for path in RESULTS.glob('*') if path.is_file()}
    write(RESULTS/'evidence-provenance.json',{'source_manifest_sha256':sha(PREPARED/'source-provenance.json'),'files_sha256':evidence})
    print(json.dumps({'report':str(RESULTS/'report.json'),'actual_terminal_scope':'Run returns normally only after all81 records.'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true'); mode.add_argument('--run',action='store_true'); options=parser.parse_args()
    prepare() if options.prepare else run()
