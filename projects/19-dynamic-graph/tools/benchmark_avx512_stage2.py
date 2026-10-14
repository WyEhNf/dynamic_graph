"""Frozen same-binary ISA pairs; prepare first, root-isolated window before run."""
import argparse,json,shutil,statistics,struct,time
from datetime import datetime,timezone
from pathlib import Path
from benchmark_grain48_stage2 import sha
from evaluate_source import run_runtime,exact_compare

def stamp():return datetime.now(timezone.utc).isoformat()
def dump(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')

def prepare(project,root):
    if root.exists():raise SystemExit('Refusing to overwrite AVX512 performance predeclaration')
    previous=project/'artifacts/stage2-avx512/correctness/report.json';proof=json.loads(previous.read_text())
    if not proof['passed'] or proof['comparisons']!=240:raise ValueError('Actual-C functional proof incomplete')
    binary=project/'build-stage2-avx512/cholesky_runtime.exe'
    if sha(binary)!=proof['runtime_sha256']:raise ValueError('Tested binary changed')
    if not all(sha(project/name)==value for name,value in proof['source_sha256'].items()):raise ValueError('Tested source changed')
    cache=project/'artifacts/stage2-grain128-holdout/reference-preparation-v2.json';prepared=json.loads(cache.read_text())
    if not prepared['passed']:raise ValueError('Real C references incomplete')
    references=[]
    for record in prepared['references']:
        if record['n'] not in (6145,8193,10000):continue
        for key in ('input','oracle'):
            path=Path(record[key]);n=record['n']
            with path.open('rb') as stream:header=stream.read(8)
            if header!=struct.pack('<II',1,n) or path.stat().st_size!=8+8*n*n or sha(path)!=record[key+'_sha256']:raise ValueError('C cache shape/hash differs')
        if record['source_sha256']!=sha(project/'fixtures/official_naive_transcribed.c'):raise ValueError('Original C source changed')
        references.append(record)
    assert len(references)==3
    root.mkdir();shutil.copyfile(binary,root/'runtime.exe')
    metadata=project/'artifacts/stage2-metadata-wire/page/schema2-dag.meta'
    prior=json.loads(metadata.with_suffix('.analysis.json').read_text())
    if prior['source_sha256']!=references[0]['source_sha256'] or prior['metadata_sha256']!=sha(metadata):raise ValueError('Metadata provenance differs')
    shutil.copyfile(metadata,root/'program.meta')
    hashes=dict(proof['source_sha256'])
    for p in (Path(__file__).resolve(),project/'tools/benchmark_grain48_stage2.py'):
        hashes[p.relative_to(project).as_posix()]=sha(p)
    for name,value in hashes.items():
        target=root/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(project/name,target)
        assert sha(target)==value
    groups=[{'n':n,'tile':b,'threads':16}for n in (6145,8193,10000)for b in (96,128)]
    schedule=[]
    for repeat in range(5):
        for index,group in enumerate(groups[repeat:]+groups[:repeat]):
            modes=['avx2','avx512']
            if (repeat+index)%2:modes.reverse()
            schedule.extend({**group,'repeat':repeat,'simd':mode}for mode in modes)
    plan={'status':'prepared_not_running','prepared_at_utc':stamp(),'source_sha256':hashes,'runtime_sha256':sha(binary),'metadata_sha256':sha(metadata),'actual_c_preparation_sha256':sha(cache),'correctness_report_sha256':sha(previous),'references':references,'groups':groups,'schedule':schedule,'repeats':5,'planned_records':60,
          'primary_refs':json.loads((project/'artifacts/stage2-avx512/initial-plan.json').read_text())['primary_refs'],
          'hypothesis':'Four-row sixteen-column AVX512F updates may reduce loop/broadcast overhead relative to four-row eight-column AVX2; Zen4 internal 256-bit paths mean no assumed gain.',
          'controls':'Identical frozen binary/Metadata/input/original-C source and outputs; explicit avx2 vs avx512 only, fixed B96 or B128, t16, tiled/dense/heap; plain strict mul then add, no implicit FMA. Both panel P/T paths remain AVX2. AUTO unchanged and unmeasured here.',
          'costs':'compute includes allocation, validation, graph, scheduling, kernel and export; Metadata/input/output IO and process wall separately preserved. Every output byte/header compared against cached real C, no tolerance.',
          'interpretation':'All five pairs per shape/geometry retained including every loss. N6145/8193 were fresh for prior B128 study, not new heldout data for this ISA study; N10000 previously measured. No source-name/hash dispatch, fitted threshold, automatic promotion or score claim.',
          'cpu_window':'Prepared only. --run requires root explicit exclusive measurement window after 18/27 functional work.'}
    dump(root/'run-plan.json',plan);print(json.dumps({'prepared':True,'planned_records':60,'performance_started':False}),flush=True)

def run(project,root):
    plan_path=root/('run-plan-v2.json' if (root/'run-plan-v2.json').exists() else 'run-plan.json');plan=json.loads(plan_path.read_text());path=root/'performance.json'
    if path.exists():raise SystemExit('Performance already dispatched; inspect existing handle')
    if not all(sha(project/name)==value for name,value in plan['source_sha256'].items()):raise ValueError('Frozen source changed')
    runtime=root/'runtime.exe';metadata=root/'program.meta'
    if sha(runtime)!=plan['runtime_sha256'] or sha(metadata)!=plan['metadata_sha256']:raise ValueError('Frozen executable/Metadata changed')
    refs={r['n']:r for r in plan['references']}
    for r in refs.values():
        if sha(r['input'])!=r['input_sha256'] or sha(r['oracle'])!=r['oracle_sha256']:raise ValueError('Real C cache changed')
    started=time.perf_counter();report={'passed':False,'status':'running','started_at_utc':stamp(),'plan_sha256':sha(plan_path),'records':[],'summary':[],'paired_ratios':[]}
    def save():report['wall_seconds']=time.perf_counter()-started;dump(path,report)
    save()
    try:
        for step in plan['schedule']:
            r=refs[step['n']];output=root/'runtime-output.bin'
            check_started=time.perf_counter()
            checks={'input':sha(r['input']),'original_c_output':sha(r['oracle']),'original_c_source':sha(project/'fixtures/official_naive_transcribed.c'),'metadata':sha(metadata),'runtime':sha(runtime)}
            if checks!={'input':r['input_sha256'],'original_c_output':r['oracle_sha256'],'original_c_source':r['source_sha256'],'metadata':plan['metadata_sha256'],'runtime':plan['runtime_sha256']}:raise ValueError('Per-trial frozen provenance differs')
            check_ms=(time.perf_counter()-check_started)*1000
            metrics=run_runtime(runtime,metadata,r['input'],output,engine='tiled',tile_size=step['tile'],threads=16,simd=step['simd'],ready_queue='heap',structure='dense')
            if metrics['effective_tile_size']!=step['tile'] or metrics['vector_kernel']!=step['simd']+'_separate_mul_add' or metrics['input_validation_kernel']!='avx2_exponent_bits':raise ValueError('Actual kernel/geometry differs from plan')
            report['records'].append({**step,**metrics,**exact_compare(r['oracle'],output),'verified_before_trial_sha256':checks,'provenance_check_ms':check_ms});save();output.unlink()
            print(json.dumps({**step,'compute_ms':metrics['compute_ms'],'byte_identical':True}),flush=True)
        fields=('compute_ms','graph_ms','kernel_ms','export_ms','input_validation_ms','metadata_read_ms','input_read_ms','output_write_ms','wall_ms')
        for group in plan['groups']:
            for mode in ('avx2','avx512'):
                rows=[r for r in report['records']if all(r[k]==v for k,v in group.items())and r['simd']==mode]
                assert len(rows)==5
                report['summary'].append({**group,'simd':mode,**{f:{'median':statistics.median(r[f]for r in rows),'min':min(r[f]for r in rows),'max':max(r[f]for r in rows)}for f in fields}})
            for repeat in range(5):
                pair={r['simd']:r for r in report['records']if all(r[k]==v for k,v in group.items())and r['repeat']==repeat}
                report['paired_ratios'].append({**group,'repeat':repeat,'compute_ratio_avx512_over_avx2':pair['avx512']['compute_ms']/pair['avx2']['compute_ms']})
        assert len(report['records'])==60 and all(sha(project/name)==value for name,value in plan['source_sha256'].items())
        report.update(passed=True,status='complete',ended_at_utc=stamp());save();print(json.dumps({'passed':True,'records':60,'wall_seconds':report['wall_seconds']}),flush=True)
    except BaseException as error:report.update(status='failed',error=repr(error));save();raise

def revise_trial_checks(project,root):
    if (root/'performance.json').exists() or (root/'run-plan-v2.json').exists():raise ValueError('Cannot revise executed/already revised plan')
    old=root/'run-plan.json';plan=json.loads(old.read_text());script=Path(__file__).resolve();name=script.relative_to(project).as_posix()
    snapshot=root/'source-v2'/name;snapshot.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(script,snapshot)
    plan['source_sha256'][name]=sha(snapshot)
    plan.update(supersedes_plan_sha256=sha(old),revised_at_utc=stamp(),revision_reason='Root requested full per-trial source/input/original-C output/Metadata/runtime SHA verification; schedule, kernel, refs, geometry unchanged. Hash time logged separately outside runtime costs.',per_trial_provenance='Rehash all actual frozen source/input/C output/Metadata/runtime before every run; record checks and check_ms. Compare every output byte afterwards.')
    dump(root/'run-plan-v2.json',plan);print(json.dumps({'revised_trial_checks':True,'planned_records':len(plan['schedule']),'performance_started':False}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--prepare',action='store_true');mode.add_argument('--run',action='store_true');mode.add_argument('--revise-trial-checks',action='store_true');args=parser.parse_args()
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-avx512/performance'
    (prepare if args.prepare else revise_trial_checks if args.revise_trial_checks else run)(project,root)
