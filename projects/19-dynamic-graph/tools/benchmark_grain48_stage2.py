"""Prepare first; run only after the root grants a quiet CPU measurement window."""
import argparse,hashlib,json,shutil,statistics,struct,time
from datetime import datetime,timezone
from pathlib import Path
from evaluate_source import run_runtime,exact_compare


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1024*1024):digest.update(block)
    return digest.hexdigest()


def stamp():return datetime.now(timezone.utc).isoformat()


def groups_and_schedule():
    configs=[{'n':n,'threads':threads,'tiles':[48,96 if threads>=8 and n>=4096 else 64],
              'role':'new B48 versus same-binary current AUTO physical tile'} for n in (2048,4096,10000) for threads in (4,16)]
    configs += [{'n':4096,'threads':16,'tiles':[64],'role':'additional B64 diagnostic anchor'},
                {'n':10000,'threads':16,'tiles':[64,128],'role':'limited B64/B128 diagnostic anchors; not a broad resweep'}]
    schedule=[]
    for repeat in range(3):
        rotated=configs[repeat:]+configs[:repeat]
        for group_index,group in enumerate(rotated):
            tiles=group['tiles'] if (repeat+group_index)%2==0 else list(reversed(group['tiles']))
            schedule.extend({'repeat':repeat,'n':group['n'],'threads':group['threads'],'tile':tile,'role':group['role']} for tile in tiles)
    return configs,schedule


def check_reference(project,n):
    # Deliberately never call ensure_dense_reference: absent cache is an error,
    # not authorization for an eight-minute original-C regeneration.
    folder=project/'artifacts'/('maximum-dense-oracle' if n==10000 else 'simd-milestone/dense-4096' if n==4096 else f'tile-milestone/dense-{n}')
    ip,oracle=folder/'input.bin',folder/'oracle.bin'
    manifest=folder/'reference-provenance.json'
    if not all(path.is_file() for path in (ip,oracle,manifest)):raise ValueError(f'Existing frozen C reference absent for N={n}')
    provenance=json.loads(manifest.read_text(encoding='utf-8'))
    for path in (ip,oracle):
        with path.open('rb') as stream:header=stream.read(8)
        if path.stat().st_size!=8+8*n*n or header!=struct.pack('<II',1,n):raise ValueError('Cache shape/header mismatch')
    actual={'source_sha256':sha(project/'fixtures/official_naive_transcribed.c'),'input_sha256':sha(ip),'oracle_sha256':sha(oracle)}
    if any(provenance[key]!=value for key,value in actual.items()):raise ValueError('Frozen original-C cache SHA mismatch')
    return {'n':n,'input':str(ip),'oracle':str(oracle),'input_bytes':ip.stat().st_size,'oracle_bytes':oracle.stat().st_size,
            'manifest':str(manifest),'manifest_sha256':sha(manifest),'original_provenance':provenance,**actual}


def prepare(project,root):
    if root.exists():raise SystemExit('Refusing to overwrite grain48 experiment')
    # Verify before creating a state that might be mistaken for running work.
    references=[check_reference(project,n) for n in (2048,4096,10000)]
    wire=project/'build-stage2-wire/cholesky_runtime.exe';baseline=project/'build/cholesky_runtime.exe'
    if sha(wire)!='d84bda7e70790b4b751aee0a877c0457f50bf9c95b086d35c1738be31061c8f2':raise ValueError('Wire runtime differs from verified candidate')
    if sha(baseline)!='2b05a6db918ced0c9c9e3bb1bfe5159ea5ed3cfee3ccb0633a538f12de409e62':raise ValueError('Historical default baseline changed')
    root.mkdir();paths=[project/'CMakeLists.txt',project/'CMakePresets.json',*sorted((project/'src').glob('*.cpp')),*sorted((project/'include').rglob('*.hpp')),
                       project/'tools/analyze_source.py',project/'tools/metadata_wire.py',project/'tools/symbolic_metadata.py',Path(__file__).resolve(),project/'tools/evaluate_source.py']
    hashes={}
    for path in paths:
        rel=path.relative_to(project);target=root/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);hashes[rel.as_posix()]=sha(target)
    shutil.copyfile(wire,root/'wire.exe');shutil.copyfile(baseline,root/'historical-baseline.exe')
    # Reuse tested schema2 Metadata without touching or recompiling the frontend.
    metadata=project/'artifacts/stage2-metadata-wire/page/schema2-dag.meta'
    prior=json.loads(metadata.with_suffix('.analysis.json').read_text(encoding='utf-8'))
    if prior['source_sha256']!=references[0]['source_sha256'] or sha(metadata)!=prior['metadata_sha256']:raise ValueError('Prior accepted source Metadata SHA mismatch')
    shutil.copyfile(metadata,root/'program.meta')
    configs,schedule=groups_and_schedule()
    plan={'status':'prepared_not_running','prepared_at_utc':stamp(),'primary_references':[
        {'title':'LAPACK DPOTRF official source/documentation','url':'https://www.netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html','application':'ILAENV-selected block granularity motivates measurements; do not substitute BLAS arithmetic for exact original-C reductions.'},
        {'title':'From Fork-Join to Asynchronous Tasks: Parallelizing Tiled Cholesky Decomposition with OpenMP and HPX','date':'2026-06-10','url':'https://arxiv.org/abs/2606.11937','application':'Task granularity trades runtime overhead against available parallelism; published EPYC results are not this laptop performance.'}],
        'hypothesis':'B48 may improve factor-cache footprint or parallel slack versus current AUTO B64/B96 while increasing queue/retirement costs; keep all negative results.',
        'binary_sha256':{'wire':sha(wire),'historical_baseline':sha(baseline)},'source_sha256':hashes,'metadata_sha256':sha(root/'program.meta'),
        'references':references,'config_groups':configs,'schedule':schedule,'repeats':3,'planned_records':len(schedule),
        'measurement':'Same frozen wire binary, forced dense/tiled/heap/auto SIMD; compute includes allocation/validation/graph/scheduling/kernel/export, excluding Metadata and IO; preserve separate fields and wall.',
        'historical_baseline_role':'Frozen for provenance only; performance compares B48 and current AUTO B64/B96 on the same wire executable, never different binaries as if single-factor tile effects.',
        'comparison':'Every run compares the full output and headers against previously independently compiled original C; no tolerance.',
        'promotion':'No automatic policy change or winner selection; repeated medians and ranges are local observations on a shared host.',
        'holdout_requirement':'Before considering any B48 policy, independently generate original-C references at predeclared fresh N3073/N6145 with tail blocks, and validate in a separate later experiment; this script does not generate those references.',
        'cpu_window':'Preparation performs hashes and copies only. --run must wait for explicit root release after project27 R39 pairing. No background dispatch.'}
    (root/'run-plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'prepared':True,'planned_records':len(schedule),'plan':str(root/'run-plan.json'),'performance_started':False}),flush=True)


def revise(project,root):
    if (root/'performance.json').exists() or (root/'run-plan-v2.json').exists():raise ValueError('Cannot revise an executed or already revised plan')
    previous=root/'run-plan.json';plan=json.loads(previous.read_text(encoding='utf-8'))
    if plan['status']!='prepared_not_running':raise ValueError('Previous plan is not unexecuted preparation')
    # Read actual source rather than assuming every current baseline uses B64.
    source=project/'src/tiled_runtime.cpp';text=source.read_text()
    geometry='workers>=8&&input.n>=4096?96u:64u'
    if geometry not in text:raise ValueError('Actual current AUTO geometry differs; inspect source before amending')
    target=root/'source-v2'/Path(__file__).resolve().relative_to(project);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(__file__,target)
    plan['source_sha256']['tools/benchmark_grain48_stage2.py']=sha(target)
    plan['supersedes_plan_sha256']=sha(previous);plan['prepared_at_utc']=stamp();plan['revision_reason']='Before any performance execution, use actual current AUTO tile (t4 all B64; t16 N2048 B64 and N4096/N10000 B96), with finite explicit B64/B128 diagnostic anchors.'
    plan['geometry_source']={'path':str(source),'sha256':sha(source),'exact_expression':geometry}
    plan['config_groups'],plan['schedule']=groups_and_schedule();plan['planned_records']=len(plan['schedule'])
    plan['hypothesis']='B48 may improve cache footprint/slack versus current AUTO B64/B96, with more queue retirements; preserve all losses.'
    plan['historical_baseline_role']='Frozen 2b05 baseline for provenance only; compare geometries on same d84 wire runtime.'
    output=root/'run-plan-v2.json';output.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'prepared':True,'planned_records':len(plan['schedule']),'plan':str(output),'performance_started':False}),flush=True)


def run(project,root):
    plan_path=root/('run-plan-v2.json' if (root/'run-plan-v2.json').exists() else 'run-plan.json');plan=json.loads(plan_path.read_text(encoding='utf-8'))
    output=root/'performance.json'
    if output.exists():raise SystemExit('Refusing to overwrite performance record; inspect the prior handle instead')
    runtime=root/'wire.exe';metadata=root/'program.meta'
    if sha(runtime)!=plan['binary_sha256']['wire'] or sha(metadata)!=plan['metadata_sha256']:raise ValueError('Frozen benchmark binary/Metadata changed')
    if not all(sha(project/name)==value for name,value in plan['source_sha256'].items()):raise ValueError('Source changed after predeclaration')
    references={}
    for reference in plan['references']:
        current=check_reference(project,reference['n'])
        if any(current[key]!=reference[key] for key in ('source_sha256','input_sha256','oracle_sha256')):raise ValueError('Original-C data changed after predeclaration')
        references[reference['n']]=current
    started=time.perf_counter();report={'passed':False,'status':'running','started_at_utc':stamp(),'plan_sha256':sha(plan_path),'plan':plan,'records':[],'summary':[]}
    def save():
        report['wall_seconds']=time.perf_counter()-started
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    save()
    try:
        for step in plan['schedule']:
            target=root/'runtime-output.bin';reference=references[step['n']]
            metrics=run_runtime(runtime,metadata,reference['input'],target,engine='tiled',tile_size=step['tile'],threads=step['threads'],simd='auto',ready_queue='heap',structure='dense')
            check=exact_compare(reference['oracle'],target)
            report['records'].append({**step,**metrics,**check});save()
            print(json.dumps({**step,'compute_ms':metrics['compute_ms'],'graph_ms':metrics['graph_ms'],'kernel_ms':metrics['kernel_ms'],'byte_identical':True}),flush=True)
            target.unlink()
        for n,threads,tile in sorted({(s['n'],s['threads'],s['tile']) for s in plan['schedule']}):
            rows=[row for row in report['records'] if (row['n'],row['threads'],row['tile'])==(n,threads,tile)]
            item={'n':n,'threads':threads,'tile':tile,'repeats':len(rows)}
            for field in ('compute_ms','graph_ms','kernel_ms','export_ms','input_validation_ms','metadata_read_ms','input_read_ms','output_write_ms','wall_ms'):
                values=[row[field] for row in rows];item[field]={'median':statistics.median(values),'min':min(values),'max':max(values)}
            report['summary'].append(item)
        assert len(report['records'])==plan['planned_records']
        assert sha(runtime)==plan['binary_sha256']['wire'] and all(sha(project/name)==value for name,value in plan['source_sha256'].items())
        report.update(passed=True,status='complete',ended_at_utc=stamp());save()
        print(json.dumps({'passed':True,'records':len(report['records']),'wall_seconds':report['wall_seconds']}),flush=True)
    except BaseException as error:
        report.update(status='failed',error=repr(error));save();raise


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--run',action='store_true')
    mode.add_argument('--revise-default-anchors',action='store_true')
    args=parser.parse_args();project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-grain48'
    if args.prepare:prepare(project,root)
    elif args.revise_default_anchors:revise(project,root)
    else:run(project,root)


if __name__=='__main__':main()
