"""Two-phase frozen full336 producer. --prepare does NO search/verification.

Only run --run after root review. Never recomputes historical baselines.
"""
import argparse
from collections import Counter
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from isa_scheduler.tree_pair_anytime import _Stop, iter_anytime_frontier
from isa_scheduler.tree_pair_anytime_refine import refine_fixed_tree_pairs_anytime
from scripts.research_spine_age_probe import check

PREPARED=ROOT/'experiments/r177-anytime-full336-prepared'
RESULTS=ROOT/'experiments/r178-anytime-full336'
SOURCE=ROOT/'experiments/r107-age-portfolio-336'
RESERVE=512*1024**2
PARAMETERS={'fixed_weight':2,'total_time_budget_ms':500,'cumulative_states':20000,'outlets_each_pair':16,'parent_max_nodes':96}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprint(data): return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def lines(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream: yield json.loads(line)
def write(path,value): path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def available(): return shutil.disk_usage(ROOT).free
def available_ram():
    class MemoryStatus(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in ('total','free','total_page','free_page','total_virtual','free_virtual','free_extended')]
    status=MemoryStatus(); status.length=ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): raise OSError('Could not read memory availability')
    return status.free


def prepare():
    if available()<RESERVE+1024**3: raise RuntimeError('Preparation needs1GiB plus512MiB reserve; no deletion/solve attempted')
    PREPARED.mkdir(exist_ok=False)
    old=read(SOURCE/'report.json'); variant=old['paired_variants']['after']
    records={r['sha256']:r for r in old['records'] if r['variant']==variant}
    cases=list(lines(SOURCE/'inputs.jsonl')); keys=[fingerprint(case['input']) for case in cases]
    assert len(cases)==len(keys)==len(set(keys))==len(records)==336
    assert Counter(r['status'] for r in records.values())==Counter({'verified':272,'proven_infeasible_under_model':47,'budget_exhausted':9,'scheduling_failure':8})
    assert sum(r.get('inserted_copies',0) for r in records.values())==192929
    historical={}
    for name in ('inputs.jsonl','optimized_outputs.jsonl','original_orders.jsonl','report.json','identity-replay.json','serialized-replay.json'):
        source=SOURCE/name; shutil.copy2(source,PREPARED/name); historical[str(source.relative_to(ROOT))]=sha(source)
    inventory=read(ROOT/'experiments/r174-anytime-full336-static/report.json')
    assert {r['sha256'] for r in inventory['records']}==set(keys)
    write(PREPARED/'static-inventory.json',inventory)
    sources=list((ROOT/'isa_scheduler').glob('*.py'))+[Path(__file__),ROOT/'scripts/research_spine_age_probe.py',
           ROOT/'research/level-stage/tree-pair-anytime-full336-plan.md',ROOT/'research/level-stage/tree-pair-full336-revised-producer.md']
    hashes={}
    for path in sources:
        target=PREPARED/'src'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
        hashes[str(path.relative_to(ROOT))]=sha(path)
    assert sha(ROOT/'isa_scheduler/tree_pair_anytime.py')=='dac3b71701e4085f7fb7e1ca2f829937cbb028cc8b68a773c1021ff16c1477c7'
    assert sha(ROOT/'isa_scheduler/tree_pair_anytime_refine.py')=='582493553cc8084270251c037e259ab004e2e6f3e88639b65693097bdf53938f'
    eligible=[r for r in inventory['records'] if r['planned_route']=='search_eligible']
    data_bank={fingerprint(case['input']):case['input'] for case in cases}
    for item in eligible:
        data=data_bank[item['sha256']]; n=item['node_count']; window=2**item['bit_width']
        assert n<=16384 and window<=32
        row_bound=item['baseline_physical_rows']+window*n
        assert len(json.dumps(data['block_id']).encode('utf-8'))<=64000
        for original in data['instructions']:
            template={'id':row_bound,'op':original['op']}
            if 'reg' in original: template['reg']=original['reg']
            if original.get('inputs'): template['inputs']=[f't#{window}']*len(original['inputs'])
            assert len(json.dumps(template).encode('utf-8'))+2<=128
        assert len(json.dumps({'id':row_bound,'op':'COPY','source':f't#{window}'}).encode('utf-8'))+2<=128
    # Diagnostic fields contain only bounded positional ints. WithN<=16384,
    # W<=32 and localparent<=96, each JSONLlabel<=1KiB/OPEN<=2KiB.
    # This is deliberately checked against actual encoded bytes during export.
    label_max=max(40000+len(r['eligible_parents']) for r in eligible)
    diagnostic_max=max((40000+len(r['eligible_parents']))*3072+len(r['eligible_parents'])*3072 for r in eligible)
    proposal_max=max(128*(r['baseline_physical_rows']+(2**r['bit_width'])*r['node_count'])+16*r['node_count']+65536 for r in eligible)
    assert diagnostic_max+2*proposal_max+64*1024**2<RESERVE
    resource={'reserve_bytes':RESERVE,'free_bytes_at_preparation':available(),
              'available_ram_bytes_at_preparation':available_ram(),'run_minimum_available_ram_bytes':768*1024**2,
              'engineering_planning_bytes':1024**3,'engineering_scope':'1GiB planning allocation plus512MiB reserve, not worst-case guarantee or ca93 extrapolation.',
              'conservative_one_input_labels_max':label_max,'conservative_one_input_diagnostic_bytes_max':diagnostic_max,
              'conservative_one_complete_output_bytes_max':proposal_max,
              'reserve_budget_argument':'512MiB exceeds current-input full diagnostic +two maximum complete files +64MiB checkpoint slack. Global proposal storage bound remains huge; stop with resource_unknown instead of dropping completed outputs.',
              'full_corpus_physical_rows_upper':inventory['resources']['conservative_all_proposal_physical_rows_upper'],
              'whole336_output_quality_mean':'undefined for64 no-incumbent inputs, never set their COPY=0',
              'memory':'Frozen raw corpus/baseline JSON banks loaded once; only current-input search references retained, eachpair streamed/disposed before next input. Preflight needs768MiB free RAM; no process termination/GPU/user-app interference.'}
    write(PREPARED/'resource-plan.json',resource)
    provenance={'frozen_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,
                'aggregate_source_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
                'historical_source_sha256':historical,'prepared_source_file_sha256':{name:sha(PREPARED/name) for name in ('inputs.jsonl','optimized_outputs.jsonl','original_orders.jsonl','report.json','static-inventory.json','resource-plan.json')},
                'parameters':PARAMETERS,'case_count':336,'initial_legal_count':272,'initial_total_copy':192929,
                'scope':'Pre-execution freeze only: copied original full336 evidence; no scheduler, oracle, verification or baseline rerun. Run phase needs root approval.'}
    write(PREPARED/'source-provenance.json',provenance)
    print(json.dumps({'prepared':str(PREPARED),'source_aggregate':provenance['aggregate_source_sha256'],'resource_plan':resource}))


def summarize(records):
    legal=[r for r in records if r['after_copies'] is not None]
    metrics={'count':len(records),'successful_count':len(legal),
             'before_statuses':dict(Counter(r['before_status'] for r in records)),
             'after_statuses':dict(Counter(r['after_status'] for r in records)),
             'candidate_outcomes':dict(Counter(r['candidate_outcome'] for r in records)),
             'before_success_total_copies':sum(r['before_copies'] for r in legal),
             'after_success_total_copies':sum(r['after_copies'] for r in legal),
             'improved_count':sum(r['after_copies']<r['before_copies'] for r in legal),
             'actual_complete_proposals':sum(r['actual_complete_proposals'] for r in records),
             'all_input_coverage_denominator':len(records),'full_input_quality_mean':None,
             'full_input_quality_mean_reason':'Any missing legal output makes wholeinput quality undefined; no zero-imputation.'}
    if legal:
        for field,label in [('before_copies','before'),('after_copies','after')]:
            metrics[label+'_success_copy_output_mean']=sum(r[field]/(r['node_count']+r[field]) for r in legal)/len(legal)
            metrics[label+'_success_copy_original_mean']=sum(r[field]/r['node_count'] for r in legal)/len(legal)
    return metrics


def export_current_input(result,key,folder):
    snapshots=result.pop('diagnostics'); attempts=result['stats']['attempts']; exports=[]
    try:
        for index,snapshot in enumerate(snapshots):
            attempt=next(item for item in attempts if item.get('diagnostic_reference')==index)
            path=folder/(key[:16]+f'-pair{index}-parent{attempt["parent"]}-frontier.jsonl')
            iterator=iter(iter_anytime_frontier(snapshot)); materialize=io=0.0; counts=Counter(); byte_count=0
            tick=perf_counter(); target=path.open('w',encoding='utf-8'); io+=perf_counter()-tick
            try:
                while True:
                    tick=perf_counter()
                    try: item=next(iterator)
                    except StopIteration: materialize+=perf_counter()-tick; break
                    materialize+=perf_counter()-tick; counts[item['kind']]+=1
                    tick=perf_counter(); payload=json.dumps(item)+'\n'; encoded_size=len(payload.encode('utf-8'))
                    limit=2048 if item['kind'] in ('open','unfinished_expansion') else 1024
                    if encoded_size>limit: raise AssertionError('Static diagnostic record byte envelope contradicted; fail closed')
                    target.write(payload); byte_count+=encoded_size; io+=perf_counter()-tick
            finally:
                tick=perf_counter(); target.close(); io+=perf_counter()-tick
            assert counts['open']==attempt['stats']['actual_open_count']
            entry={'parent':attempt['parent'],'path':str(path.relative_to(ROOT)),'sha256':sha(path),'bytes':byte_count,
                   'record_counts':dict(counts),'diagnostic_export_seconds':materialize,'diagnostic_json_io_seconds':io}
            exports.append(entry); attempt['diagnostic_export']=entry
            snapshots[index]=None; del iterator,snapshot
    finally:
        # Even an export error must release references. Do not claim complete
        # raw evidence if an I/O failure interrupted this operation.
        snapshots.clear()
    return exports


def run():
    provenance=read(PREPARED/'source-provenance.json')
    for name,digest in provenance['source_sha256'].items():
        assert sha(ROOT/name)==digest, 'Current source differs from pre-execution freeze'
    for name,digest in provenance['prepared_source_file_sha256'].items(): assert sha(PREPARED/name)==digest
    if available()<RESERVE+1024**3: raise RuntimeError('Run preflight requires1GiB plus512MiB reserve; no search started')
    if available_ram()<768*1024**2: raise RuntimeError('Run preflight needs768MiB free RAM; user apps are left alone')
    RESULTS.mkdir(exist_ok=False); started=perf_counter()
    write(RESULTS/'run-provenance.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'prepared_provenance_sha256':sha(PREPARED/'source-provenance.json'),'parameters':PARAMETERS,'reserve_bytes':RESERVE,'free_bytes_at_start':available()})
    cases=list(lines(PREPARED/'inputs.jsonl')); inventory={r['sha256']:r for r in read(PREPARED/'static-inventory.json')['records']}
    historical={r['sha256']:r for r in read(PREPARED/'report.json')['records'] if r['variant']=='age_portfolio'}
    outputs={r['input_sha256']:r['output'] for r in lines(PREPARED/'optimized_outputs.jsonl') if r['variant']=='age_portfolio'}
    orders={r['input_sha256']:r['original_order'] for r in lines(PREPARED/'original_orders.jsonl') if r['variant']=='age_portfolio'}
    # Exactly once before any candidate search. Frozen existing correctness is
    # not reused as a substitute for current independent replay.
    prechecks=[]; pre_tick=perf_counter()
    for case in cases:
        data=case['input']; key=fingerprint(data)
        if key in outputs:
            tick=perf_counter(); check(data,outputs[key],orders[key])
            assert sum(row['op']=='COPY' for row in outputs[key]['optimized_instructions'])==historical[key]['inserted_copies']
            prechecks.append({'sha256':key,'four_checks_passed':True,'seconds':perf_counter()-tick})
    assert len(prechecks)==272
    write(RESULTS/'baseline-prechecks.json',{'count':272,'elapsed_seconds':perf_counter()-pre_tick,'records':prechecks,'scope':'Original identity/order/window/hazards, independent symbolic and3localinteger replay; no baseline scheduler.'})
    records=[]; resource_halt=None
    # Existing full outputs remain referenced by prepared immutable JSONL;
    # save final outputs compactly to a separate stream, not duplicated banks.
    with (RESULTS/'best_outputs.jsonl').open('w',encoding='utf-8') as final_stream:
        for case in cases:
            data=case['input']; key=fingerprint(data); initial=historical[key]; route=inventory[key]['planned_route']
            before=initial.get('inserted_copies'); baseline=None if key not in outputs else {'output':outputs[key],'original_order':orders[key]}
            best=None if baseline is None else {**baseline,'copies':before}; paths=[]; exports=[]; stats=None; proposal_io=0.0
            candidate_seconds=flow_seconds=verify_seconds=0.0; candidate_outcome=route
            if resource_halt is None and available()<RESERVE+64*1024**2: resource_halt='pre_input_reserve'
            if resource_halt is not None: candidate_outcome='resource_unknown_not_executed'
            elif route=='search_eligible':
                def sink(parent,candidate):
                    nonlocal proposal_io,resource_halt
                    tick=perf_counter(); payload=json.dumps({'input_sha256':key,'parent':parent,**candidate})+'\n'
                    payload_size=len(payload.encode('utf-8'))
                    low=available()<RESERVE+payload_size
                    path=RESULTS/(key[:16]+f'-parent{parent}-candidate{len(paths)}-output.json')
                    # Reserve is intentionally large enough to save this actual
                    # complete proposal plus all captured diagnostics before
                    # requesting the core's existing interruption return.
                    try: path.write_text(payload,encoding='utf-8')
                    except OSError:
                        resource_halt='artifact_io_failure'; raise
                    paths.append(path); proposal_io+=perf_counter()-tick
                    if low:
                        resource_halt='proposal_reserve_after_saved_complete'
                        raise _Stop('producer_resource_reserve_after_saved_complete')
                tick=perf_counter()
                result=refine_fixed_tree_pairs_anytime(data,baseline,time_budget_ms=500,max_states=20000,max_outcomes=16,max_parent_nodes=96,on_completed=sink)
                candidate_seconds=perf_counter()-tick; best=result['best']; stats=result['stats']; candidate_outcome=stats['outcome']
                if resource_halt is not None: candidate_outcome='resource_unknown_after_saved_complete'
                # Search has stopped. Current-input emergency reserve covers
                # export even after low-space stop; no further search begins.
                if available()<RESERVE: resource_halt=resource_halt or 'pre_export_reserve'; candidate_outcome='resource_unknown_after_search'
                tick=perf_counter(); exports=export_current_input(result,key,RESULTS); flow_seconds=perf_counter()-tick
                del result
                tick=perf_counter()
                for path in paths:
                    complete=read(path); check(data,complete['output'],complete['original_order'])
                check(data,best['output'],best['original_order']); verify_seconds=perf_counter()-tick
                assert best['copies']<=before
            if best is not None:
                final_stream.write(json.dumps({'input_sha256':key,'output':best['output'],'original_order':best['original_order'],'copies':best['copies']})+'\n'); final_stream.flush()
            record={'sha256':key,'family':case['family'],'node_count':len(data['instructions']),'bit_width':data['bit_width'],
                    'before_status':initial['status'],'after_status':initial['status'] if best is None else 'verified',
                    'before_copies':before,'after_copies':None if best is None else best['copies'],'planned_route':route,
                    'candidate_outcome':candidate_outcome,'historical_failure_or_certificate':initial.get('error'),
                    'actual_complete_proposals':len(paths),'stats':stats,'candidate_seconds_before_export':candidate_seconds,
                    'complete_json_io_inside_deadline_seconds':proposal_io,'diagnostic_flow_seconds':flow_seconds,
                    'diagnostic_export_seconds':sum(e['diagnostic_export_seconds'] for e in exports),
                    'diagnostic_json_io_seconds':sum(e['diagnostic_json_io_seconds'] for e in exports),
                    'verify_seconds':verify_seconds,'complete_output_bytes':sum(p.stat().st_size for p in paths),
                    'diagnostic_bytes':sum(e['bytes'] for e in exports),'resource_halt_reason':resource_halt}
            records.append(record); write(RESULTS/'partial-records.json',records)
            # Only compact stats/filepaths remain at next-input boundary.
            paths.clear(); exports.clear(); del best,baseline,stats
    assert len(records)==336
    report={**summarize(records),'families':{family:summarize([r for r in records if r['family']==family]) for family in sorted({r['family'] for r in records})},
            'records':records,'parameters':PARAMETERS,'reserve_bytes':RESERVE,'resource_halt':resource_halt,'elapsed_seconds':perf_counter()-started,
            'scope':'All original336 retained, same272 original baselines inclunsupported/zero,47/9/8 original failures retained. No DPfallback/gaincomposition/default/oracle/baseline rerun. Search stop/diagnostic/JSONIO/verification separately measured, not isolated speed or officialLevel.'}
    write(RESULTS/'report.json',report)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in RESULTS.glob('*') if p.is_file()}
    write(RESULTS/'evidence-provenance.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'evidence_sha256':evidence})
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','families')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--prepare',action='store_true'); parser.add_argument('--run',action='store_true'); option=parser.parse_args()
    if option.prepare==option.run: parser.error('Choose exactly one phase; --run requires root review')
    if option.prepare: prepare()
    else:
        try: run()
        except Exception as error:
            # Preserve partial files; never relabel failed artifact export as
            # a verified outcome or delete difficult inputs. A failed run is
            # not automatically retried or silently completed.
            if RESULTS.exists():
                try: write(RESULTS/'run-failure.json',{'error_type':type(error).__name__,'error':str(error),
                      'candidate_outcome':'resource_unknown' if isinstance(error,OSError) else 'actual_failed_run',
                      'all_input_denominator':336,'scope':'Actual failed run, partial evidence retained; unexecuted inputs are unknown, no claimed all336 completion or missing-output zero imputation.'})
                except OSError: pass
            raise
