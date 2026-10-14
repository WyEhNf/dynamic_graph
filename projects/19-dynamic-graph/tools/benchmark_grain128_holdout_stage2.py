"""Original-C fresh references first; isolated performance requires a later release."""
import argparse,json,shutil,statistics,struct,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from evaluate_source import compile_oracle,make_input,run_runtime,exact_compare
from benchmark_grain48_stage2 import sha,check_reference


def stamp():return datetime.now(timezone.utc).isoformat()


def prepare(project,root):
    if root.exists():raise SystemExit('Refusing to overwrite heldout study')
    runtime=project/'build-stage2-wire/cholesky_runtime.exe';source=project/'fixtures/official_naive_transcribed.c'
    if sha(runtime)!='d84bda7e70790b4b751aee0a877c0457f50bf9c95b086d35c1738be31061c8f2':raise ValueError('Verified frozen Runtime changed')
    geometry='workers>=8&&input.n>=4096?96u:64u'
    if geometry not in (project/'src/tiled_runtime.cpp').read_text():raise ValueError('Inspect current AUTO before preparing')
    existing=check_reference(project,10000)
    root.mkdir();frozen=root/'source';hashes={}
    paths=[project/'CMakeLists.txt',project/'CMakePresets.json',*sorted((project/'src').glob('*.cpp')),*sorted((project/'include').rglob('*.hpp')),source,Path(__file__).resolve(),project/'tools/evaluate_source.py',project/'tools/benchmark_grain48_stage2.py']
    for path in paths:
        target=frozen/path.relative_to(project);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);hashes[path.relative_to(project).as_posix()]=sha(target)
    shutil.copyfile(runtime,root/'runtime.exe')
    metadata=project/'artifacts/stage2-metadata-wire/page/schema2-dag.meta';analysis=json.loads(metadata.with_suffix('.analysis.json').read_text())
    if analysis['source_sha256']!=sha(source) or analysis['metadata_sha256']!=sha(metadata):raise ValueError('Accepted Metadata provenance changed')
    shutil.copyfile(metadata,root/'program.meta')
    groups=[{'n':6145,'role':'new heldout shape with tail blocks'},{'n':8193,'role':'new heldout shape with tail blocks'},{'n':10000,'role':'previously measured shape; five-round repeat, not heldout'}]
    schedule=[]
    for repeat in range(5):
        for index,group in enumerate(groups[repeat%3:]+groups[:repeat%3]):
            variants=[('AUTO96','auto',96),('B128',128,128)]
            if (repeat+index)%2:variants.reverse()
            schedule.extend({**group,'repeat':repeat,'variant':label,'tile_argument':tile,'expected_tile':expected,'threads':16} for label,tile,expected in variants)
    plan={'status':'references_preparing_performance_not_started','prepared_at_utc':stamp(),'source_sha256':hashes,'runtime_sha256':sha(runtime),'metadata_sha256':sha(root/'program.meta'),'actual_auto_expression':geometry,
          'primary_references':[{'url':'https://www.netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html','application':'Granularity tradeoff only; source-order arithmetic remains unchanged'},
                                {'url':'https://arxiv.org/abs/2606.11937','application':'Task overhead versus parallel slack; no transfer of published machine performance'}],
          'original_c_contract':'Frozen actual official-page-transcribed C; local div=x/y, madd=x*y+z nonfused, L initialized +0; independent GCC -O2 -fno-fast-math -ffp-contract=off. Not supplied official test package.',
          'new_reference_shapes':[6145,8193],'repeat_reference':existing,'schedule':schedule,'repeats':5,'planned_records':30,
          'measurements':'Same frozen runtime, dense/tiled/heap/auto SIMD; actual AUTO argument must report B96. Full compute includes allocation/validation/graph/scheduling/kernel/export, excludes Metadata/IO; preserve all separate counters and process wall.',
          'retention':'Keep every predeclared trial, whole-file original-C equality and every loss. No automatic promotion, no fitted threshold or changed kernel.',
          'interpretation':'Assess each fresh shape separately with all five paired ratios, medians and full ranges; contradictory or noisy improvements are insufficient for a cross-shape policy. N10000 repeat is not fresh evidence.',
          'cpu_window':'This preparation may execute original C to generate ground truth, which is not a performance attribution. --run waits for root CPU isolation release after project18/27 functional work.'}
    (root/'run-plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    started=time.perf_counter();report={'passed':False,'status':'running','started_at_utc':stamp(),'plan_sha256':sha(root/'run-plan.json'),'references':[existing]}
    def save():
        report['wall_seconds']=time.perf_counter()-started
        (root/'reference-preparation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    save()
    try:
        frozen_c=frozen/'fixtures/official_naive_transcribed.c';gcc='E:/mingw64/bin/gcc.exe'
        begin=time.perf_counter();oracle=compile_oracle(frozen_c,'cholesky',root/'oracle-build',gcc);compile_seconds=time.perf_counter()-begin
        report['oracle_build']={'source_sha256':sha(frozen_c),'harness_sha256':sha(root/'oracle-build/oracle.c'),'executable_sha256':sha(oracle),'compiler':subprocess.run([gcc,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],'compile_wall_seconds':compile_seconds};save()
        for n in plan['new_reference_shapes']:
            folder=root/f'dense-{n}';folder.mkdir();ip=folder/'input.bin';output=folder/'oracle.bin'
            begin=time.perf_counter();make_input(ip,[n]);input_seconds=time.perf_counter()-begin
            pending={'n':n,'status':'original_c_running','input':str(ip),'oracle':str(output),'source_sha256':sha(frozen_c),'input_sha256':sha(ip),'input_generation_wall_seconds':input_seconds,'oracle_started_at_utc':stamp()}
            report['active_reference']=pending;save();print(json.dumps({'phase':'original_c_running','n':n,'input_seconds':input_seconds}),flush=True)
            begin=time.perf_counter();subprocess.run([str(oracle),str(ip),str(output),'32'],check=True);oracle_seconds=time.perf_counter()-begin
            for path in (ip,output):
                with path.open('rb') as stream:header=stream.read(8)
                if path.stat().st_size!=8+8*n*n or header!=struct.pack('<II',1,n):raise ValueError('Original C binary shape/header mismatch')
            record={**pending,'status':'complete','oracle_sha256':sha(output),'oracle_bytes':output.stat().st_size,'input_bytes':ip.stat().st_size,'oracle_wall_seconds':oracle_seconds,'oracle_executable_sha256':sha(oracle),'oracle_generation':'Actual separately GCC-compiled frozen original C source; candidate not executed for ground truth'}
            (folder/'reference-provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8');report['references'].append(record);report.pop('active_reference');save()
            print(json.dumps({'phase':'original_c_complete','n':n,'oracle_seconds':oracle_seconds,'bytes':output.stat().st_size}),flush=True)
        assert all(sha(project/name)==value for name,value in hashes.items())
        report.update(passed=True,status='complete_performance_not_started',ended_at_utc=stamp());save()
        print(json.dumps({'prepared':True,'references':len(report['references']),'wall_seconds':report['wall_seconds'],'performance_started':False}),flush=True)
    except BaseException as error:
        report.update(status='failed',error=repr(error));save();raise


def repair_labels(project,root):
    if (root/'performance.json').exists() or (root/'run-plan-v2.json').exists():raise ValueError('Cannot repair after performance dispatch or a prior repair')
    old_plan=root/'run-plan.json';old_prepared=root/'reference-preparation.json'
    plan=json.loads(old_plan.read_text());prepared=json.loads(old_prepared.read_text())
    if not prepared['passed'] or prepared['status']!='complete_performance_not_started':raise ValueError('Original C did not complete')
    for record in prepared['references']:
        if record['n'] in plan['new_reference_shapes']:
            actual=root/f"dense-{record['n']}"/'oracle.bin'
            if sha(actual)!=record['oracle_sha256'] or actual.stat().st_size!=record['oracle_bytes']:raise ValueError('Actual fresh C file differs from completed SHA')
            record['oracle_generation']=record['oracle'];record['oracle']=str(actual)
            record['supersedes_reference_sha256']=sha(actual.parent/'reference-provenance.json')
            (actual.parent/'reference-provenance-v2.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    frozen=root/'source-v2/tools'/Path(__file__).name;frozen.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(__file__,frozen)
    plan['source_sha256']['tools/'+Path(__file__).name]=sha(frozen)
    plan.update(supersedes_plan_sha256=sha(old_plan),revision_reason='Before any candidate execution, repair the overwritten oracle path label by keeping description in oracle_generation; schedule, original C files and SHA, native/frontend/binary unchanged.',revised_at_utc=stamp())
    (root/'run-plan-v2.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    prepared.update(plan_sha256=sha(root/'run-plan-v2.json'),supersedes_preparation_sha256=sha(old_prepared))
    (root/'reference-preparation-v2.json').write_text(json.dumps(prepared,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'repaired_labels':True,'original_c_not_repeated':True,'performance_started':False}),flush=True)


def run(project,root):
    plan_path=root/('run-plan-v2.json' if (root/'run-plan-v2.json').exists() else 'run-plan.json')
    prepared_path=root/('reference-preparation-v2.json' if (root/'reference-preparation-v2.json').exists() else 'reference-preparation.json')
    plan=json.loads(plan_path.read_text());prepared=json.loads(prepared_path.read_text())
    if not prepared['passed'] or prepared['status']!='complete_performance_not_started':raise ValueError('Original C references not complete')
    path=root/'performance.json'
    if path.exists():raise SystemExit('Performance already dispatched; inspect existing handle rather than restart')
    runtime=root/'runtime.exe';metadata=root/'program.meta'
    if sha(runtime)!=plan['runtime_sha256'] or sha(metadata)!=plan['metadata_sha256']:raise ValueError('Frozen executable/Metadata changed')
    if not all(sha(project/name)==value for name,value in plan['source_sha256'].items()):raise ValueError('Source changed since predeclaration')
    references={}
    for item in prepared['references']:
        if sha(Path(item['input']))!=item['input_sha256'] or sha(Path(item['oracle']))!=item['oracle_sha256']:raise ValueError('Original-C cache changed')
        references[item['n']]=item
    started=time.perf_counter();report={'passed':False,'status':'running','started_at_utc':stamp(),'plan_sha256':sha(plan_path),'records':[],'summary':[],'paired_ratios':[]}
    def save():
        report['wall_seconds']=time.perf_counter()-started;path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    save()
    try:
        for step in plan['schedule']:
            reference=references[step['n']];output=root/'runtime-output.bin'
            metrics=run_runtime(runtime,metadata,reference['input'],output,engine='tiled',tile_size=step['tile_argument'],threads=16,simd='auto',ready_queue='heap',structure='dense')
            if metrics['effective_tile_size']!=step['expected_tile']:raise ValueError('Actual AUTO/explicit geometry differs from plan')
            report['records'].append({**step,**metrics,**exact_compare(reference['oracle'],output)});save();output.unlink()
            print(json.dumps({**step,'compute_ms':metrics['compute_ms'],'byte_identical':True}),flush=True)
        for n in (6145,8193,10000):
            for variant in ('AUTO96','B128'):
                rows=[row for row in report['records'] if row['n']==n and row['variant']==variant];item={'n':n,'variant':variant,'repeats':len(rows)}
                for field in ('compute_ms','graph_ms','kernel_ms','export_ms','input_validation_ms','metadata_read_ms','input_read_ms','output_write_ms','wall_ms'):
                    values=[row[field] for row in rows];item[field]={'median':statistics.median(values),'min':min(values),'max':max(values)}
                report['summary'].append(item)
            for repeat in range(5):
                pair={row['variant']:row for row in report['records'] if row['n']==n and row['repeat']==repeat}
                report['paired_ratios'].append({'n':n,'repeat':repeat,'compute_ratio_B128_over_AUTO96':pair['B128']['compute_ms']/pair['AUTO96']['compute_ms']})
        assert len(report['records'])==30 and all(sha(project/name)==value for name,value in plan['source_sha256'].items())
        report.update(passed=True,status='complete',ended_at_utc=stamp());save();print(json.dumps({'passed':True,'records':30,'wall_seconds':report['wall_seconds']}),flush=True)
    except BaseException as error:
        report.update(status='failed',error=repr(error));save();raise


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--prepare',action='store_true');mode.add_argument('--run',action='store_true');mode.add_argument('--repair-reference-labels',action='store_true');args=parser.parse_args()
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-grain128-holdout'
    if args.prepare:prepare(project,root)
    elif args.repair_reference_labels:repair_labels(project,root)
    else:run(project,root)


if __name__=='__main__':main()
