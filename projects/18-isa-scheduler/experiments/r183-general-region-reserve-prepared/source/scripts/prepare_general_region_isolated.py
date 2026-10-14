"""R182 source/fixture/layout freeze ONLY. Does not execute any search/test."""
import hashlib
import ast
import argparse
import json
from pathlib import Path
import random
import shutil
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from isa_scheduler.general_region_anytime import resource_layout


def fixture(seed,bits):
    rng=random.Random(seed); n=rng.randint(5,9); rows=[]; values=[]
    for index in range(n):
        if not values or index<2 or rng.random()<.32:
            row={'id':index,'op':'GET','reg':f'r{rng.randrange(3)}'}; values.append(index)
        elif index==n-1 or rng.random()<.22:
            source=rng.choice(values); row={'id':index,'op':'SET','reg':f'r{rng.randrange(3)}','inputs':[f't#{index-source}']}
        else:
            left=rng.choice(values); right=rng.choice(values)
            row={'id':index,'op':rng.choice(['ADD','MULW']),'inputs':[f't#{index-left}',f't#{index-right}']}; values.append(index)
        rows.append(row)
    return {'block_id':f'general_raw_{seed}_w{2**bits}','bit_width':bits,'instructions':rows}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--round',default='r182-general-region-isolated-prepared')
    options=parser.parse_args()
    if '/' in options.round or '\\' in options.round: raise SystemExit('Round must be a directory basename')
    dest=ROOT/'experiments'/options.round
    if dest.exists(): raise SystemExit('Freeze destination already exists; no overwrite')
    dest.mkdir(parents=True)
    cases=[fixture(182000+i,2+i%4) for i in range(80)]
    with (dest/'inputs.jsonl').open('w',encoding='utf-8',newline='\n') as stream:
        for case in cases: stream.write(json.dumps(case,ensure_ascii=False,separators=(',',':'))+'\n')
    source_paths=['isa_scheduler/general_region_anytime.py','isa_scheduler/general_region_refine.py',
        'isa_scheduler/model.py','isa_scheduler/identity_witness.py','isa_scheduler/raw_pure.py','isa_scheduler/verify.py',
        'scripts/raw_general_region_oracle.py','scripts/prepare_general_region_isolated.py',
        'tests/test_general_region_contracts.py','research/level-stage/general-dag-region-plan.md',
        'research/level-stage/general-dag-region-resource-clarification.md',
        'research/level-stage/general-region-hand11.json','research/level-stage/general-region-isolated-contract.md']
    entries=[]
    for relative in source_paths:
        target=dest/'source'/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(ROOT/relative,target)
        entries.append({'path':relative,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size})
        if relative.endswith('.py'): ast.parse(target.read_text(encoding='utf-8'),filename=relative)
    hand=json.loads((ROOT/'research/level-stage/general-region-hand11.json').read_text(encoding='utf-8'))
    # Inspecting saved JSON/layout does not verify or solve hand witness.
    print('Hand fixture keys:',','.join(hand))
    original=hand['input']; baseline=hand['baseline']
    layouts=[{'fixture':'hand11','layout':resource_layout(original,baseline)}]
    maximum={'block_id':'max-layout-16384','bit_width':5,'instructions':[
        {'id':i,'op':'GET','reg':str(i)} for i in range(16384)]}
    maxinc={'output':{'block_id':maximum['block_id'],'optimized_instructions':maximum['instructions']},
            'original_order':list(range(16384))}
    layouts.append({'fixture':'synthetic-layout-only-N16384-W32-F16384','layout':resource_layout(maximum,maxinc)})
    manifest={'phase':'Prepared only; no solver/oracle/contracts executed','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_files':entries,'source_aggregate_sha256':hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest(),
        'input_count':80,'input_sha256':hashlib.sha256((dest/'inputs.jsonl').read_bytes()).hexdigest(),
        'resource_layouts':layouts,'parameters':{'ms':500,'expansions':20000,'transition_attempts':20000,
        'region_nodes':32,'max_regions':64,'outlets_each_region':16,'reserve_bytes':536870912},
        'future_oracle':{'N_max':9,'expanded_max':20000,'discovered_max':20000,'ms':500,
                         'all_old_COPY':True,'early_COPY':True,'unknown_retained':True}}
    (dest/'source-provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'prepared':str(dest),'input_count':80,'source_sha256':manifest['source_aggregate_sha256'],
        'layout_records':layouts,'solver_execution':False},ensure_ascii=False))


if __name__=='__main__': main()
