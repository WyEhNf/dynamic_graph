"""Two-phase R186 prepare / R187 fixed original336 execution (not yet run).

R178 saved incumbents only; no baseline algorithm/oracle/default execution.
Lossless gzip stores every completed proposal and all diagnostic labels.
"""
import argparse
import ast
from collections import Counter
import ctypes
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from isa_scheduler.general_region_anytime import resource_layout,iter_region_frontier
from isa_scheduler.general_region_refine import refine_general_regions
from scripts.research_general_region_isolated import four_check,resources
from scripts.general_region_incremental_replay import IncrementalRegionReplay

SOURCE=ROOT/'experiments/r178-anytime-full336'
INPUT=ROOT/'experiments/r177-anytime-full336-prepared/inputs.jsonl'
PREPARED=ROOT/'experiments/r186-general-region-full336-prepared'
RESULTS=ROOT/'experiments/r187-general-region-full336'
RESERVE=512*1024**2; MIN_RAM=768*1024**2
PARAMETERS={'ms':500,'expansions':20000,'transitions':20000,'region_nodes':32,'regions':64,'outlets_each_region':16}


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024**2),b''): digest.update(chunk)
    return digest.hexdigest()
def fingerprint(data): return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def jsonline(value): return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8')
def write(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def lines(path,compressed=False):
    opener=gzip.open if compressed else open
    with opener(path,'rt',encoding='utf-8') as stream:
        for line in stream: yield json.loads(line)
def save_gzip(path,value):
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=1) as stream: stream.write(jsonline(value))
def gzip_copy(source,target):
    with source.open('rb') as incoming,target.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=1) as outgoing:
            shutil.copyfileobj(incoming,outgoing,1024**2)
def read_initial(key): return next(lines(PREPARED/'initials'/f'{key}.json.gz',True))
def available_ram():
    class Status(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in (
            'total','free','total_page','free_page','total_virtual','free_virtual','free_extended')]
    status=Status(); status.length=ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): raise OSError('RAM availability read failed')
    return status.free


def prepare():
    PREPARED.mkdir(exist_ok=False); (PREPARED/'initials').mkdir()
    historical=read(SOURCE/'report.json'); old={row['sha256']:row for row in historical['records']}
    assert len(old)==336 and Counter(row['after_status'] for row in old.values())==Counter({
        'verified':272,'proven_infeasible_under_model':47,'budget_exhausted':9,'scheduling_failure':8})
    initials={}; initial_files={}
    for row in lines(SOURCE/'best_outputs.jsonl'):
        key=row['input_sha256']; initial={name:row[name] for name in ('output','original_order','copies')}
        assert key not in initials and initial['copies']==old[key]['after_copies']
        save_gzip(PREPARED/'initials'/f'{key}.json.gz',initial); initials[key]=initial
        initial_files[key]=sha(PREPARED/'initials'/f'{key}.json.gz')
    assert len(initials)==272 and sum(item['copies'] for item in initials.values())==192902
    gzip_copy(INPUT,PREPARED/'inputs.jsonl.gz'); gzip_copy(SOURCE/'report.json',PREPARED/'historical-r178-report.json.gz')
    inventory=[]; seen=set()
    for case in lines(INPUT):
        data=case['input']; key=fingerprint(data); seen.add(key); row=old[key]; initial=initials.get(key)
        layout=None if initial is None else resource_layout(data,initial)
        package=None if layout is None else layout['diagnostic_bound_bytes']+2*layout['complete_proposal_bound_bytes']+64*1024**2
        inventory.append({'sha256':key,'family':case['family'],'node_count':len(data['instructions']),
            'bit_width':data['bit_width'],'source_status':row['after_status'],'before_copies':row['after_copies'],
            'prior_candidate_outcome':row['candidate_outcome'],'historical_failure_or_certificate':row.get('historical_failure_or_certificate'),
            'resource_layout':layout,'input_package_bound_bytes':package,
            'planned_route':'no_incumbent_preserved' if initial is None else 'zero_copy_retained' if initial['copies']==0 else 'general_region_search',
            'package_supported':None if package is None else package<=RESERVE})
    assert seen==set(old) and len(inventory)==336
    paths=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'scripts/general_region_incremental_replay.py',
        ROOT/'scripts/general_region_raw_checks.py',ROOT/'scripts/raw_general_region_oracle.py',
        ROOT/'scripts/research_general_region_isolated.py',ROOT/'research/level-stage/general-region-full336-runner.md']
    source_hashes={}
    for path in paths:
        relative=str(path.relative_to(ROOT)); target=PREPARED/'src'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target); source_hashes[relative]=sha(path)
        if path.suffix=='.py': ast.parse(path.read_text(encoding='utf-8'),filename=relative)
    assert source_hashes['isa_scheduler\\general_region_anytime.py']=='263e3eeac936a06da7383ef5c51fbbcd6057a7efaae9dd81f015756feda81eec'
    assert source_hashes['isa_scheduler\\general_region_refine.py']=='8e1cdf3a57aa609fddf4582efe155f0257f538ff4e504da410da0d5878461438'
    write(PREPARED/'inventory.json',inventory)
    resources_plan={'reserve_bytes':RESERVE,'minimum_free_RAM_bytes':MIN_RAM,'actual_preparation':resources(),
        'available_RAM_at_preparation':available_ram(),'package_max_bytes':max(row['input_package_bound_bytes'] or 0 for row in inventory),
        'proposal_uncompressed_max_bytes':max(row['resource_layout']['complete_proposal_bound_bytes'] if row['resource_layout'] else 0 for row in inventory),
        'global_uncompressed_proposal_upper_bytes':sum(1024*row['resource_layout']['complete_proposal_bound_bytes'] for row in inventory if row['planned_route']=='general_region_search'),
        'scope':'Global bound intentionally huge; gzip ratio not assumed. Actual reserve triggers resource_unknown tail, no old deletion or diagnostic sampling.'}
    write(PREPARED/'resource-plan.json',resources_plan)
    manifest={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':source_hashes,
        'source_aggregate_sha256':hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest(),
        'initial_files_sha256':initial_files,'prepared_sha256':{name:sha(PREPARED/name) for name in (
            'inputs.jsonl.gz','historical-r178-report.json.gz','inventory.json','resource-plan.json')},
        'original_source_sha256':{'inputs.jsonl':sha(INPUT),'r178-report':sha(SOURCE/'report.json'),'r178-best-bank':sha(SOURCE/'best_outputs.jsonl')},
        'parameters':PARAMETERS,'count':336,'legal_initials':272,'before_copies':192902,
        'phase':'Preparation only; no verification/search/oracle/baseline/default executed.'}
    write(PREPARED/'source-provenance.json',manifest)
    print(json.dumps({'prepared':str(PREPARED),'source_sha256':manifest['source_aggregate_sha256'],
        'routes':dict(Counter(row['planned_route'] for row in inventory)),'resources':resources_plan,'solver_executed':False}))


def export(data,initial,result,key):
    snapshots=result.pop('diagnostics'); exports=[]
    for index,snapshot in enumerate(snapshots):
        start=result['stats']['attempts'][index]['start']; path=RESULTS/f'{key[:16]}-region{index}-frontier.jsonl.gz'
        replay=IncrementalRegionReplay(data,initial,start); count=Counter(); decoded_bytes=0; digest=hashlib.sha256()
        materialize=jsonio=rawcheck=0.0; tick=perf_counter()
        with path.open('wb') as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=1) as stream:
                iterator=iter(iter_region_frontier(snapshot))
                while True:
                    clock=perf_counter()
                    try: row=next(iterator)
                    except StopIteration: materialize+=perf_counter()-clock; break
                    materialize+=perf_counter()-clock; count[row['kind']]+=1
                    clock=perf_counter(); encoded=jsonline(row)
                    if len(encoded)>(2048 if row['kind'] in ('open','unfinished_expansion') else 1024):
                        raise AssertionError('Diagnostic serialized envelope exceeded')
                    stream.write(encoded); digest.update(encoded); decoded_bytes+=len(encoded); jsonio+=perf_counter()-clock
                    clock=perf_counter(); replay.accept(row); rawcheck+=perf_counter()-clock
        exports.append({'start':start,'path':str(path.relative_to(ROOT)),'compressed_sha256':sha(path),
            'decoded_sha256':digest.hexdigest(),'compressed_bytes':path.stat().st_size,'decoded_bytes':decoded_bytes,
            'counts':dict(count),'independent_replayed_records':replay.replayed,'materialize_seconds':materialize,
            'gzip_jsonio_seconds':jsonio,'raw_replay_seconds':rawcheck,'whole_export_seconds':perf_counter()-tick})
        snapshots[index]=None; del snapshot,replay
    snapshots.clear(); return exports


def summarize(records):
    legal=[row for row in records if row['before_copies'] is not None]
    result={'count':len(records),'legal_initial_count':len(legal),'source_statuses':dict(Counter(row['source_status'] for row in records)),
        'candidate_outcomes':dict(Counter(row['candidate_outcome'] for row in records)),
        'before_copies':sum(row['before_copies'] for row in legal),'after_copies':sum(row['after_copies'] for row in legal),
        'improved_count':sum(row['after_copies']<row['before_copies'] for row in legal),
        'actual_complete_outputs':sum(row.get('actual_complete_outputs',0) for row in records),
        'all_input_quality_mean':None,'all_input_quality_mean_reason':'64 no-incumbent source statuses remain, never imputed zero.'}
    for label in ('before','after'):
        result[label+'_legal_copy_output_mean']=sum(row[label+'_copies']/(row['node_count']+row[label+'_copies']) for row in legal)/len(legal) if legal else None
        result[label+'_legal_copy_original_mean']=sum(row[label+'_copies']/row['node_count'] for row in legal)/len(legal) if legal else None
    return result


def run():
    manifest=read(PREPARED/'source-provenance.json')
    for relative,expected in manifest['source_sha256'].items():
        if sha(ROOT/relative)!=expected: raise AssertionError('Source changed: '+relative)
    for name,expected in manifest['prepared_sha256'].items():
        if sha(PREPARED/name)!=expected: raise AssertionError('Prepared file changed: '+name)
    for key,expected in manifest['initial_files_sha256'].items():
        if sha(PREPARED/'initials'/f'{key}.json.gz')!=expected: raise AssertionError('Initial changed: '+key)
    RESULTS.mkdir(exist_ok=False); shutil.copyfile(PREPARED/'source-provenance.json',RESULTS/'source-provenance.json')
    inventory={row['sha256']:row for row in read(PREPARED/'inventory.json')}; records=[]; initial_checks={}; started=perf_counter(); current=None
    halt=None
    try:
        # Baseline validation is a separate pass, never a scheduler/oracle rerun.
        with (RESULTS/'initial-checks.jsonl').open('w',encoding='utf-8') as stream:
            for case in lines(PREPARED/'inputs.jsonl.gz',True):
                data=case['input']; key=fingerprint(data); entry=inventory[key]; current=key
                if entry['before_copies'] is None: continue
                if resources()['disk_free_bytes']<RESERVE or available_ram()<MIN_RAM:
                    halt='resource_before_initial_check'; initial_checks[key]={'outcome':'not_checked_resource_unknown'}; continue
                initial=read_initial(key); tick=perf_counter(); check=four_check(data,initial)
                initial_checks[key]={'outcome':'verified','seconds':perf_counter()-tick,'check':check}
                stream.write(jsonline(dict(initial_checks[key],sha256=key)).decode()); stream.flush(); del initial
        for case in lines(PREPARED/'inputs.jsonl.gz',True):
            data=case['input']; key=fingerprint(data); current=key; entry=inventory[key]; tick=perf_counter(); before=resources()
            record={name:entry[name] for name in ('sha256','family','node_count','bit_width','source_status','before_copies','historical_failure_or_certificate')}
            record.update(after_copies=entry['before_copies'],actual_complete_outputs=0,compressed_complete_bytes=0,
                          decoded_complete_bytes=0,diagnostic_exports=[],candidate_outcome='no_incumbent_'+entry['source_status'],
                          baseline_check=initial_checks.get(key),resources_before=before)
            if entry['before_copies'] is not None:
                initial=read_initial(key)
                if halt is not None or before['disk_free_bytes']<RESERVE or available_ram()<MIN_RAM:
                    halt=halt or 'resource_before_input'; record['candidate_outcome']='not_executed_resource_unknown'; record['resource_reason']=halt
                elif entry['before_copies']==0: record['candidate_outcome']='verified_zero_copy_retained'
                else:
                    complete_path=RESULTS/f'{key[:16]}-complete.jsonl.gz'; count=0; decoded=0; sink_seconds=0.0; rss=[before['working_set_bytes']]
                    with complete_path.open('wb') as raw:
                        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=1) as stream:
                            def sink(start,candidate):
                                nonlocal count,decoded,sink_seconds
                                clock=perf_counter(); encoded=jsonline({'input_sha256':key,'region_start':start,'candidate':candidate})
                                stream.write(encoded); stream.flush(); raw.flush(); decoded+=len(encoded); count+=1
                                sink_seconds+=perf_counter()-clock; rss.append(resources()['working_set_bytes'])
                            clock=perf_counter(); result=refine_general_regions(data,initial,on_completed=sink,resource_snapshot=resources)
                            search_seconds=perf_counter()-clock
                    clock=perf_counter(); checked=0
                    for output in lines(complete_path,True): four_check(data,output['candidate']); checked+=1
                    if checked!=count: raise AssertionError('Complete sink count differs from saved gzip rows')
                    four_check(data,result['best']); verify_seconds=perf_counter()-clock
                    exports=export(data,initial,result,key); rss.append(resources()['working_set_bytes'])
                    record.update(candidate_outcome=result['stats']['outcome'],stats=result['stats'],after_copies=result['best']['copies'],
                        actual_complete_outputs=count,compressed_complete_bytes=complete_path.stat().st_size,decoded_complete_bytes=decoded,
                        complete_gzip_sha256=sha(complete_path),diagnostic_exports=exports,sampled_RSS_max_bytes=max(rss),
                        timing={'search_including_sink_seconds':search_seconds,'sink_gzip_jsonio_seconds':sink_seconds,'full_four_verify_seconds':verify_seconds})
                    if 'resource' in result['stats']['outcome']: halt='resource_halt_after_current_input'
                    best=result['best']; del result
                    save_gzip(RESULTS/f'{key[:16]}-best.json.gz',dict(best,input_sha256=key)); del best
                del initial
            after=resources(); record['resources_after']=after; record['whole_input_seconds']=perf_counter()-tick
            if after['disk_free_bytes']<RESERVE: halt='resource_after_current_export'
            records.append(record); write(RESULTS/'partial-records.json',records)
            print(json.dumps({key:record[key] for key in ('sha256','family','candidate_outcome','before_copies','after_copies','actual_complete_outputs')}),flush=True)
        report=summarize(records); report['records']=records; report['elapsed_seconds']=perf_counter()-started
        report['baseline_checks']=dict(Counter(item['outcome'] for item in initial_checks.values()))
        report['families']={family:summarize([row for row in records if row['family']==family]) for family in sorted({row['family'] for row in records})}
        report['scope']='Original336/R178 same saved272 initials; original47/9/8 retained; candidate resource tail explicit unknown; no officialLevel/oracle/default/baseline rerun.'
        write(RESULTS/'report.json',report)
    except BaseException as error:
        write(RESULTS/'failure.json',{'input_sha256':current,'type':type(error).__name__,'message':str(error),
            'completed_records':len(records),'elapsed_seconds':perf_counter()-started,'automatic_restart':False})
        raise
    write(RESULTS/'evidence-provenance.json',{'source_manifest_sha256':sha(PREPARED/'source-provenance.json'),
        'files_sha256':{path.name:sha(path) for path in RESULTS.glob('*') if path.is_file()}})
    print(json.dumps({'report':str(RESULTS/'report.json'),'records':len(records)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true'); mode.add_argument('--run',action='store_true'); options=parser.parse_args()
    prepare() if options.prepare else run()
