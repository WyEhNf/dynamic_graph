"""Read frozen evidence only: ca93 attribution and complete336 coverage plan.

Never imports a scheduler, parser, matcher, verifier or oracle. This static
inventory does not replace the mandatory independent replay before execution.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def lines(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
def write(path, data): path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def raw_forest(data):
    """Input-only structural inventory equivalent to current forest screen.

    This deliberately does not assert semantic legality of saved outputs.
    Exact shared operands are deduplicated only when counting data consumers.
    """
    rows = data['instructions']; args = []; users = [0]*len(rows)
    gets = []; sets = []
    if 2**data['bit_width'] < 2: return None, 'window_below_two'
    for position, row in enumerate(rows):
        op = row['op']
        if op not in ('GET', 'SET', 'ADD', 'MULW'): return None, 'unsupported_original_opcode'
        if op == 'GET': gets.append(row['reg'])
        if op == 'SET': sets.append(row['reg'])
        children = tuple(dict.fromkeys(position-int(ref[2:]) for ref in row.get('inputs', [])))
        for child in children:
            if not 0 <= child < position or rows[child]['op']=='SET': return None, 'invalid_data_reference'
            users[child] += 1
        args.append(children)
    if len(set(gets))!=len(gets) or len(set(sets))!=len(sets) or set(gets)&set(sets):
        return None, 'register_uniqueness_or_hazard_scope'
    if max(users, default=0)>1: return None, 'shared_data_identity'
    if any(not users[i] and row['op'] not in ('GET', 'SET') for i, row in enumerate(rows)):
        return None, 'dead_arithmetic'
    return args, None


def selector_inventory(data, output, order, children):
    """O(n+physicalrows) static ranking inventory, no search invocation."""
    ranks = {node:rank for rank,node in enumerate(order)}
    sizes=[]; branch=[]; minima=[]; maxima=[]
    for i,kids in enumerate(children):
        sizes.append(1+sum(sizes[c] for c in kids))
        branch.append(len(kids)==2 or any(branch[c] for c in kids))
        minima.append(min([ranks[i]]+[minima[c] for c in kids]))
        maxima.append(max([ranks[i]]+[maxima[c] for c in kids]))
    history=[]; cursor=0; by_identity=Counter(); by_cursor=Counter()
    for row in output['optimized_instructions']:
        if row['op']=='COPY':
            identity=history[len(history)-int(row['source'][2:])]
            by_identity[identity]+=1; by_cursor[cursor]+=1
        else:
            identity=order[cursor]; cursor+=1
            if row['op']=='SET': identity=None
        history.append(identity)
    prefix=[0]
    for rank in range(len(order)+1): prefix.append(prefix[-1]+by_cursor[rank])
    candidates=[]
    for parent,kids in enumerate(children):
        if len(kids)!=2 or not any(branch[c] for c in kids) or sizes[parent]>96: continue
        start,end=minima[parent],maxima[parent]
        if end-start+1!=sizes[parent] or order[end]!=parent: continue
        candidates.append([parent,sum(by_identity[c] for c in kids),prefix[end+1]-prefix[start],sizes[parent]])
    candidates.sort(key=lambda item:(-item[1],-item[2],item[3],item[0]))
    return candidates


def freeze(folder, sources, evidence):
    hashes={}
    for path in sources:
        target=folder/'src'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target); hashes[str(path.relative_to(ROOT))]=sha(path)
    record={'frozen_utc':datetime.now(timezone.utc).isoformat(), 'source_sha256':hashes,
            'aggregate_source_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
            'read_only_evidence_sha256':{str(path.relative_to(ROOT)):sha(path) for path in evidence},
            'scope':'Static saved-evidence analysis only. No search/oracle/baseline rerun, no full336 execution, no default change.'}
    write(folder/'source-provenance.json', record)


def attribution():
    source=ROOT/'experiments/r172-tree-pair-anytime-84'
    folder=ROOT/'experiments/r173-anytime-ca93-static'; folder.mkdir(exist_ok=False)
    report=read(source/'report.json'); record=next(r for r in report['records'] if r['sha256'].startswith('ca93'))
    key=record['sha256']; short=key[:16]
    baseline_path=source/(short+'-baseline-output.json'); dp_path=source/(short+'-dp-actual-output.json')
    baseline=read(baseline_path); dp=read(dp_path)
    results=[]; evidence=[source/'report.json',source/'inputs.jsonl',baseline_path,dp_path]
    for attempt in record['attempt']['stats']['attempts']:
        stats=attempt['stats']; sides=stats['sides']; projections=[]
        for side in sides:
            members=set(side); actual=[node for node in dp['original_order'] if node in members]
            mismatch=next((i for i,(a,b) in enumerate(zip(side,actual)) if a!=b),None)
            projections.append({'side_original_order':side,'dp_witness_projection':actual,
                                'exact_equal':side==actual,'first_mismatch_offset':mismatch})
        path=ROOT/attempt['diagnostic_export']['path']; evidence.append(path)
        endpoints=[row for row in lines(path) if row['kind'] in ('frontier_header','open','unfinished_expansion')]
        results.append({'parent':attempt['parent'],'outcome':attempt['outcome'],
                        'processed_states':attempt['processed_states'], 'complete_outputs':attempt['complete_outputs'],
                        'elapsed_ms':attempt['elapsed_ms'], 'dp21_witness_within_fixed_side_orders':all(p['exact_equal'] for p in projections),
                        'projections':projections,'actual_terminal_frontier':endpoints})
    proposals=[]
    for path in sorted(source.glob(short+'-parent*-candidate*-output.json')):
        value=read(path); evidence.append(path)
        proposals.append({'path':str(path.relative_to(ROOT)), 'parent':value['parent'],
                          'actual_copies':sum(row['op']=='COPY' for row in value['output']['optimized_instructions']),
                          'declared_copies':value['copies'],'original_order':value['original_order']})
    report={'input_sha256':key,'initial_copies':record['before_copies'],'old_dp_copies':record['dp_actual_copies'],
            'awa_copies':record['after_copies'],'wrapper_outcome':record['attempt']['outcome'],
            'processed_states':record['attempt']['stats']['processed_states'],
            'wrapper_search_elapsed_ms':record['attempt']['stats']['elapsed_ms'],
            'eligible_parent_order':record['attempt']['stats']['eligible_parents'], 'actual_attempts':results,
            'all_complete_proposals':proposals,'proposal_copy_distribution':dict(Counter(p['actual_copies'] for p in proposals)),
            'attribution':'First ranked parent62 exhausted its fixed-side/deadline improvement family. Parent61 stopped at 16 complete proposals, all non-improving; parent59 (the oldDP21 proposal) was not attempted. 7580<20000 and saved149ms<500ms: this regression is an outlet-cap/ranking effect, not time/state exhaustion. The particular savedDP21 order fails fixed-side projection in the two attempted families; this does not prove no alternative21 witness in those families. Any OPEN/unfinished g+h is only a necessary full-row lower bound, never reachability/optimality.',
            'scope':'Saved R172 evidence only; no queue reconstruction, frontier continuation, candidate rerun or DP fallback.'}
    write(folder/'report.json',report)
    freeze(folder,[Path(__file__)],evidence)
    return report


def coverage():
    source=ROOT/'experiments/r107-age-portfolio-336'
    folder=ROOT/'experiments/r174-anytime-full336-static'; folder.mkdir(exist_ok=False)
    old=read(source/'report.json'); variant=old['paired_variants']['after']
    before={r['sha256']:r for r in old['records'] if r['variant']==variant}
    outputs={r['input_sha256']:r['output'] for r in lines(source/'optimized_outputs.jsonl') if r['variant']==variant}
    orders={r['input_sha256']:r['original_order'] for r in lines(source/'original_orders.jsonl') if r['variant']==variant}
    records=[]; families=defaultdict(Counter)
    for case in lines(source/'inputs.jsonl'):
        data=case['input']; key=fingerprint(data); historical=before[key]; status=historical['status']
        args, reason=raw_forest(data); output=outputs.get(key); order=orders.get(key)
        if (output is not None)!=(status=='verified') or (order is not None)!=(status=='verified'):
            raise AssertionError('Saved output/order coverage disagrees with full336 record')
        copies=historical.get('inserted_copies'); eligibility=[]
        if output is None: route='no_incumbent_'+status
        elif copies==0: route='verified_zero_copy_retained'
        elif args is None: route='verified_incumbent_retained_unsupported'
        else:
            eligibility=selector_inventory(data,output,order,args)
            route='search_eligible' if eligibility else 'verified_incumbent_retained_no_pair'
        item={'sha256':key,'family':case['family'],'node_count':len(data['instructions']), 'bit_width':data['bit_width'],
              'before_status':status,'before_copies':copies,'planned_route':route,'forest_screen_reason':reason,
              'eligible_parents':eligibility,'baseline_physical_rows':None if output is None else len(output['optimized_instructions'])}
        records.append(item); families[case['family']][route]+=1
    assert len(records)==336 and len(before)==336 and len(outputs)==272 and len(orders)==272
    r172=ROOT/'experiments/r172-tree-pair-anytime-84'; actual_outputs=list(r172.glob('*candidate*-output.json'))
    diag=list(r172.glob('*frontier.jsonl')); actual_size=sum(p.stat().st_size for p in actual_outputs+diag)
    routes=Counter(r['planned_route'] for r in records); eligible=[r for r in records if r['planned_route']=='search_eligible']
    legal=[r for r in records if r['before_status']=='verified']
    upper_proposals=sum(min(40000,16*len(r['eligible_parents'])) for r in eligible)
    # Each expanded state has at most two generated successors and goals.
    # Unexpanded seed labels are possible for every exhausted pair.
    upper_labels=sum(40000+len(r['eligible_parents']) for r in eligible)
    # Existing original prefix is preserved byte/row-wise. New emission emits
    # <=W-1 deadline relays before each original, else fails closed.
    upper_proposal_rows=sum(min(40000,16*len(r['eligible_parents']))*(r['baseline_physical_rows']+(2**r['bit_width'])*r['node_count']) for r in eligible)
    resource={'observed_free_disk_bytes':shutil.disk_usage(ROOT).free,
              'saved_source_bundle_bytes':sum((source/name).stat().st_size for name in ('inputs.jsonl','optimized_outputs.jsonl','original_orders.jsonl','report.json')),
              'r172_actual_complete_files':len(actual_outputs),'r172_actual_complete_bytes':sum(p.stat().st_size for p in actual_outputs),
              'r172_actual_diagnostic_files':len(diag),'r172_actual_diagnostic_bytes':sum(p.stat().st_size for p in diag),
              'r172_actual_saved_candidate_plus_diagnostic_bytes':actual_size,
              'eligible_inputs':len(eligible),'static_eligible_pairs':sum(len(r['eligible_parents']) for r in eligible),
              'conservative_all_complete_proposal_count_upper':upper_proposals,
              'conservative_all_immutable_label_count_upper':upper_labels,
              'conservative_all_proposal_physical_rows_upper':upper_proposal_rows,
              'warning':'Row/count bounds are finite but intentionally loose; 500ms does not bound disk bytes, diagnostic/JSONIO, verification or end-to-end wall time. No worst-case fitting-disk claim. Preflight free-space and streaming disk reserve required; halt with resource_unknown rather than silently discard completed proposals.'}
    report={'source_folder':str(source.relative_to(ROOT)),'source_variant':variant,'case_count':336,
            'before_statuses':dict(Counter(r['before_status'] for r in records)),'planned_routes':dict(routes),
            'all_families':{name:dict(counts) for name,counts in sorted(families.items())},
            'before_successful_count':len(legal),'before_successful_total_copies':sum(r['before_copies'] for r in legal),
            'before_success_copy_output_mean':sum(r['before_copies']/(r['node_count']+r['before_copies']) for r in legal)/len(legal),
            'before_success_copy_original_mean':sum(r['before_copies']/r['node_count'] for r in legal)/len(legal),
            'fixed_parameters':{'weight':2,'total_ms_each_input':500,'cumulative_states_each_input':20000,'outlets_each_pair':16,'parent_max_nodes':96},
            'resources':resource,'records':records,
            'scope':'Static input-only inventory, not saved-output replay or execution. All336 statuses and families retained; candidate applies only to supported saved-incumbent forest pairs. Legal success means have denominator272; whole336 quality mean undefined for64 missing outputs, never substitute zero or claim officialLevel.'}
    write(folder/'report.json',report)
    sources=[Path(__file__),ROOT/'isa_scheduler/tree_pair_anytime.py',ROOT/'isa_scheduler/tree_pair_anytime_refine.py',ROOT/'research/level-stage/tree-pair-anytime-full336-plan.md']
    evidence=[source/name for name in ('inputs.jsonl','optimized_outputs.jsonl','original_orders.jsonl','report.json','identity-replay.json','serialized-replay.json')]
    evidence.extend([r172/'report.json',r172/'source-provenance.json',r172/'evidence-provenance.json'])
    freeze(folder,sources,evidence)
    return {k:v for k,v in report.items() if k!='records'}


if __name__=='__main__':
    attribution_report=attribution()
    print(json.dumps({'ca93_proposal_costs':attribution_report['proposal_copy_distribution']}))
    print(json.dumps(coverage(),ensure_ascii=False))
