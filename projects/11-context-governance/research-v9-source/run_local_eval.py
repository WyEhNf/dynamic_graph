"""Paired real-model evaluation with functional tests and transparent metrics."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

from .bundles import load_case
from .core import PreparedContext, govern, render
from .local_model import LocalModel
from .quality import check_code
from .selftest_suite import build_suite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--suite', default='fixtures/selftest-v2')
    parser.add_argument('--output', default='artifacts/local-model-evaluation.json')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--budget', type=int, default=650)
    parser.add_argument('--max-new-tokens', type=int, default=256)
    parser.add_argument('--device', default='auto')
    parser.add_argument('--attention', choices=['auto','native','expanded'], default='auto')
    parser.add_argument('--prompt-policy', choices=['original-v1','requirements-v2','concise-v3'], default='concise-v3')
    parser.add_argument('--diagnostic-input-count',action='store_true',help='Include full rejected-input token counting in request timing')
    parser.add_argument('--metrics-db',default='artifacts/session-metrics.sqlite3')
    parser.add_argument('--prefill-chunk',type=int,default=0,help='Bound prefill activation size without dropping prompt tokens')
    parser.add_argument('--quantization',choices=['none','nf4'],default='none',help='Optional NF4 changes weights; evaluate quality separately from FP16')
    parser.add_argument('--self-review',action='store_true',help='Second generation sees only requirements, context and draft; no hidden test feedback')
    parser.add_argument('--contract-feedback',action='store_true',help='Derive optional static AST review hints only from public spec/draft/target')
    parser.add_argument('--prepared-context',action='store_true',help='Amortize immutable context indexing and fragment costs within a caller-owned session')
    parser.add_argument('--rebuild-suite', action='store_true')
    args = parser.parse_args()
    if args.contract_feedback and not args.self_review: parser.error('contract feedback requires self-review')
    if args.repeats < 1: parser.error('repeats must be positive')
    suite = Path(args.suite)
    if (suite/'manifest.json').exists() and not args.rebuild_suite:
        ids=json.loads((suite/'manifest.json').read_text(encoding='utf-8'))['case_ids']
    else:
        ids=build_suite(suite)
    started_unix=time.time()
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    from .session_metrics import SessionMetrics
    ledger=SessionMetrics(args.metrics_db)
    session_id=Path(args.output).stem+'-'+str(time.time_ns())
    model = LocalModel(args.model, args.device, attention=args.attention, prompt_policy=args.prompt_policy,prefill_chunk=args.prefill_chunk,quantization=args.quantization)
    model.generate(model.prompt('Warmup.', 'Return def identity(x): return x'), 32)
    # Warm both prompt lengths before recording latency, so initial CUDA setup is excluded.
    first_metadata, _, first_spec, first_items = load_case(suite, ids[0])
    model.generate(model.prompt(render(first_items), first_spec), 8)
    first_comp = govern(first_spec, first_items, args.budget, model.counter, first_metadata['context_dependencies'])
    model.generate(model.prompt(first_comp['context'], first_spec), 8)
    report = {'origin':'self-created paired test; not official score', 'model':str(Path(args.model).resolve()),
              'model_manifest':model.manifest, 'model_files_verified':True,
              'device':model.device, 'python':platform.python_version(), 'torch':model.torch.__version__,
              'repeats':args.repeats, 'budget_context_tokens':args.budget, 'cases':[],
              'started_unix':started_unix, 'source_sha256_at_start':source_hashes,
              'request_full_input_counting':args.diagnostic_input_count,
              'metrics_session':session_id,
              'prefill_chunk_tokens':model.prefill_chunk,
              'weight_quantization':model.quantization,
              'self_review':args.self_review,'prepared_context':args.prepared_context,
              'contract_feedback':args.contract_feedback,
              'attention_backend':model.attention, 'prompt_policy':model.prompt_policy,
              'generation':'greedy, do_sample=False', 'fixture_version':json.loads((suite/'manifest.json').read_text())['version'],
              'ttft_definition':'request start including tokenization/transfer through first generated token callback; synchronized CUDA; excludes model loading/warmup',
              'limitations':['Self-created Python coding tasks do not establish general code quality.',
                             f'This model context is {model.model.config.max_position_embeddings}; 128K is tested separately for importance analysis only.',
                             'Runs alternate order; shared-machine contention can affect latency.']}
    for case_index, case_id in enumerate(ids):
        metadata, snapshot, spec, items = load_case(suite, case_id)
        test_file = suite / 'tests' / f'{case_id}.py'
        oracle = check_code((suite / 'oracle' / f'{case_id}.py').read_text(encoding='utf-8'), snapshot, metadata['target_file'], test_file)
        if not oracle['passed']: raise RuntimeError(f'invalid test oracle {case_id}: {oracle}')
        prepare_start=time.perf_counter_ns()
        prepared=PreparedContext(items,metadata['context_dependencies']) if args.prepared_context else None
        prepare_ms=(time.perf_counter_ns()-prepare_start)/1e6
        governed = govern(spec, items, args.budget, model.counter, metadata['context_dependencies'],prepared=prepared)
        baseline_prompt = model.prompt(render(items), spec)
        compressed_prompt = model.prompt(governed['context'], spec)
        runs = {'baseline':[], 'compressed':[]}
        for repeat in range(args.repeats):
            order = ['baseline','compressed'] if (repeat+case_index)%2==0 else ['compressed','baseline']
            for mode in order:
                request_start=time.perf_counter_ns()
                if mode=='baseline':
                    prompt=model.prompt(render(items),spec)
                    governance_ms=0.0
                else:
                    run_governance=govern(spec,items,args.budget,model.counter,metadata['context_dependencies'],
                                         measure_input=args.diagnostic_input_count,prepared=prepared)
                    prompt=model.prompt(run_governance['context'],spec)
                    governance_ms=run_governance['metrics']['governance_ms']
                request_overhead_ms=(time.perf_counter_ns()-request_start)/1e6
                generation = model.generate(prompt, args.max_new_tokens)
                final_code_ms=(time.perf_counter_ns()-request_start)/1e6
                extra={}
                if args.self_review:
                    draft=generation
                    context=render(items) if mode=='baseline' else run_governance['context']
                    review_start=time.perf_counter_ns()
                    feedback=None
                    if args.contract_feedback:
                        from .contract_audit import audit_draft
                        feedback=audit_draft(spec,draft.output,(snapshot/metadata['target_file']).read_text(encoding='utf-8'))
                    review_prompt=model.review_prompt(context,spec,draft.output,feedback)
                    review_overhead_ms=(time.perf_counter_ns()-review_start)/1e6
                    review=model.generate(review_prompt,args.max_new_tokens)
                    final_code_ms=(time.perf_counter_ns()-request_start)/1e6
                    # Evaluate only after both generations. The review cannot
                    # receive the draft's trusted functional outcome.
                    draft_functional=check_code(draft.output,snapshot,metadata['target_file'],test_file)
                    extra={'draft':asdict(draft),'draft_functional':draft_functional,
                           'review_feedback':feedback,
                           'review':asdict(review),'review_prompt_sha256':hashlib.sha256(review_prompt.encode()).hexdigest(),
                           'review_request_overhead_ms':review_overhead_ms}
                    from .local_model import Generation
                    generation=Generation(review.output,draft.ttft_ms,
                        draft.elapsed_ms+review_overhead_ms+review.elapsed_ms,
                        draft.input_tokens+review.input_tokens,draft.output_tokens+review.output_tokens)
                functional = check_code(generation.output, snapshot, metadata['target_file'], test_file)
                runs[mode].append({**asdict(generation), **extra, 'functional':functional, 'repeat':repeat, 'order':order.index(mode),
                                   'request_overhead_ms':request_overhead_ms,'governance_ms':governance_ms,
                                   'time_to_final_code_ms':final_code_ms,
                                   'end_to_end_ttft_ms':request_overhead_ms+generation.ttft_ms})
                print(json.dumps({'case':case_id,'mode':mode,'repeat':repeat,'passed':functional['passed'],'ttft_ms':generation.ttft_ms}, ensure_ascii=False), flush=True)
        base = runs['baseline']; compressed = runs['compressed']
        case = {'id':case_id,'snapshot_sha256':metadata['snapshot_sha256'], 'governance':governed,
                'context_prepare_ms':prepare_ms,
                'tests_sha256':hashlib.sha256(test_file.read_bytes()).hexdigest(),
                'baseline_prompt_sha256':hashlib.sha256(baseline_prompt.encode()).hexdigest(),
                'compressed_prompt_sha256':hashlib.sha256(compressed_prompt.encode()).hexdigest(), 'runs':runs,
                'baseline_pass':all(r['functional']['passed'] for r in base),
                'compressed_pass':all(r['functional']['passed'] for r in compressed),
                'compression_ratio':1-compressed[0]['input_tokens']/base[0]['input_tokens'],
                'baseline_ttft_median_ms':statistics.median(r['ttft_ms'] for r in base),
                'compressed_ttft_median_ms':statistics.median(r['ttft_ms'] for r in compressed)}
        case['ttft_reduction'] = 1-case['compressed_ttft_median_ms']/case['baseline_ttft_median_ms']
        case['baseline_end_to_end_ttft_ms']=statistics.median(r['end_to_end_ttft_ms'] for r in base)
        case['compressed_end_to_end_ttft_ms']=statistics.median(r['end_to_end_ttft_ms'] for r in compressed)
        case['end_to_end_ttft_reduction'] = 1-case['compressed_end_to_end_ttft_ms']/case['baseline_end_to_end_ttft_ms']
        case['time_to_final_code_reduction']=1-statistics.median(r['time_to_final_code_ms'] for r in compressed)/statistics.median(r['time_to_final_code_ms'] for r in base)
        if args.self_review:
            case['draft_baseline_pass']=all(r['draft_functional']['passed'] for r in base)
            case['draft_compressed_pass']=all(r['draft_functional']['passed'] for r in compressed)
            case['review_regressions']=[mode for mode,group in runs.items() if any(r['draft_functional']['passed'] and not r['functional']['passed'] for r in group)]
        for repeat,(base_run,comp_run) in enumerate(zip(base,compressed)):
            ledger.record_pair(session_id,f'{case_id}:{repeat}',
                baseline_tokens=base_run['input_tokens'],compressed_tokens=comp_run['input_tokens'],
                baseline_ttft_ms=base_run['end_to_end_ttft_ms'],compressed_ttft_ms=comp_run['end_to_end_ttft_ms'],
                baseline_correct=base_run['functional']['passed'],compressed_correct=comp_run['functional']['passed'],
                importance_ms=governed['metrics']['importance_analysis_ms'],governance_ms=comp_run['governance_ms'],
                provenance={'case':case_id,'snapshot_sha256':metadata['snapshot_sha256'],'model':model.manifest['repo']})
        report['cases'].append(case)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    baseline_pass = sum(c['baseline_pass'] for c in report['cases'])
    compressed_pass = sum(c['compressed_pass'] for c in report['cases'])
    regressions = [c['id'] for c in report['cases'] if c['baseline_pass'] and not c['compressed_pass']]
    report['summary'] = {'cases':len(ids), 'baseline_pass':baseline_pass, 'compressed_pass':compressed_pass,
                         'paired_regressions':regressions, 'quality_gate_passed':baseline_pass>0 and not regressions and compressed_pass>=baseline_pass,
                         'all_compressed_correct':compressed_pass==len(ids),
                         'mean_compression_ratio':statistics.mean(c['compression_ratio'] for c in report['cases']),
                         'mean_ttft_reduction':statistics.mean(c['ttft_reduction'] for c in report['cases']),
                         'mean_end_to_end_ttft_reduction':statistics.mean(c['end_to_end_ttft_reduction'] for c in report['cases']),
                         'mean_time_to_final_code_reduction':statistics.mean(c['time_to_final_code_reduction'] for c in report['cases']),
                         'importance_max_ms':max(c['governance']['metrics']['importance_analysis_ms'] for c in report['cases'])}
    if args.self_review:
        report['summary']['draft_baseline_pass']=sum(c['draft_baseline_pass'] for c in report['cases'])
        report['summary']['draft_compressed_pass']=sum(c['draft_compressed_pass'] for c in report['cases'])
        report['summary']['review_regressions']={c['id']:c['review_regressions'] for c in report['cases'] if c['review_regressions']}
        report['limitations'].append('TTFT still measures the first draft token. Time to final code includes both live generation calls; cumulative token counts include draft and review prompts. Hidden tests are run after both calls, outside those times.')
    report['finished_unix'] = time.time()
    report['wall_seconds_including_load_warmup_and_checks']=report['finished_unix']-started_unix
    from .resources import resource_snapshot
    report['resources']=resource_snapshot(model)
    report['session_summary']=ledger.summary(session_id)
    report['summary']['total_model_generation_seconds']=sum(
        (run['draft']['elapsed_ms']+run['review']['elapsed_ms'] if 'draft' in run else run['elapsed_ms'])/1000
        for case in report['cases'] for runs in case['runs'].values() for run in runs)
    report['final_code_timing_scope']='Live wall clock from request start until final model output decoded, before trusted functional tests.'
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
