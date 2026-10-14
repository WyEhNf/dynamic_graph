"""Run verified COPY refinement from an existing schedule or a fresh baseline.

Usage: python -m isa_scheduler.refine input.json --incumbent output.json
       --output improved.json --time-budget-ms 500
"""
import argparse
import gzip
import json
from pathlib import Path
import sys
from time import perf_counter

from .identity_witness import check_identity_witness
from .model import InvalidBlock, BudgetExceeded, InfeasibleSchedule
from .online_mobile_refine import refine_online_mobile
from .optimizer import optimize
from .verify import verify


def normalize_incumbent(value):
    """Accept a research witness package or a normal optimize result."""
    if not isinstance(value,dict):
        raise InvalidBlock('Incumbent must be an object with a complete original-order witness')
    if 'output' in value:
        output=value['output'];order=value.get('original_order')
    else:
        output=value;order=value.get('stats',{}).get('original_order')
    if not isinstance(output,dict) or not isinstance(output.get('optimized_instructions'),list):
        raise InvalidBlock('Incumbent optimized_instructions are missing')
    if not isinstance(order,list):
        raise InvalidBlock('Incumbent needs original_order; a strict export alone has no identity witness')
    return {'output':output,'original_order':order,
            'copies':sum(row.get('op')=='COPY' for row in output['optimized_instructions'])}


def refine(data, incumbent=None, *, time_budget_ms=500, max_states=20000,
           initial_strategy='age_portfolio', initial_time_budget_ms=100):
    started=perf_counter()
    if incumbent is None:
        incumbent=optimize(data,initial_strategy,time_budget_ms=initial_time_budget_ms)
    initial=normalize_incumbent(incumbent)
    check_identity_witness(data,initial['output'],initial['original_order'])
    verify(data,initial['output'])
    result=refine_online_mobile(data,initial,time_budget_ms=time_budget_ms,
                               max_states=max_states,max_transitions=max_states)
    best=result['best']
    identity=check_identity_witness(data,best['output'],best['original_order'])
    verify(data,best['output'])
    if best['copies']>initial['copies']:
        raise AssertionError('Refinement cannot increase COPY count')
    output=dict(best['output'])
    output['stats']={'strategy':'online_mobile_refinement','original_order':best['original_order'],
        'inserted_copy_count':best['copies'],'initial_copy_count':initial['copies'],
        'copy_reduction':initial['copies']-best['copies'],
        'identity_verification':identity,'refinement':result['stats'],
        'elapsed_ms_including_initial_and_checks':(perf_counter()-started)*1000,
        'budget_scope':'Refinement has its own shared wall/work cap; optional initial scheduling and all verification are additional.'}
    return output


def read(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',encoding='utf-8-sig') as stream:return json.load(stream)


def main():
    parser=argparse.ArgumentParser(description='Verified online mobile COPY refinement')
    parser.add_argument('input',type=Path)
    parser.add_argument('--incumbent',type=Path,help='Existing output with stats.original_order or research witness package; gzip accepted')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--time-budget-ms',type=float,default=500)
    parser.add_argument('--max-states',type=int,default=20000)
    parser.add_argument('--initial-strategy',choices=('auto','age_portfolio'),default='age_portfolio')
    parser.add_argument('--initial-time-budget-ms',type=float,default=100)
    args=parser.parse_args()
    try:
        output=refine(read(args.input),None if args.incumbent is None else read(args.incumbent),
            time_budget_ms=args.time_budget_ms,max_states=args.max_states,
            initial_strategy=args.initial_strategy,initial_time_budget_ms=args.initial_time_budget_ms)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'output':str(args.output),'before_copies':output['stats']['initial_copy_count'],
            'after_copies':output['stats']['inserted_copy_count'],
            'outcome':output['stats']['refinement']['outcome']}))
        return 0
    except (InvalidBlock,BudgetExceeded,InfeasibleSchedule,ValueError) as error:
        print(str(error),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
