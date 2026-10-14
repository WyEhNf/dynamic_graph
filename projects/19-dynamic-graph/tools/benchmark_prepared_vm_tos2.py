"""Predeclare TOS2 versus unchanged decoded operands in the same candidate."""
import argparse,hashlib,json,math,shutil,statistics,struct,subprocess,time
from pathlib import Path
from evaluate_source import exact_compare
from windows_resource_probe import monitored_run
def sha(path):
    h=hashlib.sha256()
    with path.open('rb')as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def repeat_original_matrix_stream(source,target,repeats):
    # Each matrix is copied, with only the outer M header recomputed. Reference
    # matrix bytes are exclusively the previously executed original-C outputs.
    data=source.read_bytes();m=struct.unpack('<I',data[:4])[0]
    with target.open('wb')as out:
        out.write(struct.pack('<I',m*repeats))
        for _ in range(repeats):out.write(data[4:])
def prepare(project,root):
    stage=project/'artifacts/stage2-prepared-vm-phase2';proof=json.loads((stage/'correctness/report.json').read_text());assert proof['passed']
    root.mkdir(exist_ok=False);shutil.copyfile(Path(__file__),root/'benchmark-script.py');shutil.copyfile(project/'tools/windows_resource_probe.py',root/'windows_resource_probe.py');shutil.copyfile(stage/'candidate.exe',root/'runtime.exe')
    plan={'status':'predeclared','version':1,'phase':'TOS2 stack only versus phase1 decoded algorithm in the same new EXE; no goto/fusion/plan cache','runtime_sha256':sha(root/'runtime.exe'),'frozen_phase1_sha256':proof['phase1_sha256'],'script_sha256':sha(root/'benchmark-script.py'),'resource_probe_sha256':sha(root/'windows_resource_probe.py'),'host_load':'actual Win32 CPU/working-set/host available RAM counters per process; isolate project CPU jobs only, no assumption that user applications are idle; no interference with user applications','rounds':5,'records':120,'target_original_steps_per_trial':40000000,'repeat_rule':'ceil(target / frozen dense VM steps); all twelve sources included including fresh holdouts and explicit FMA; no timing-dependent selection','pair_order':'decoded/decoded-tos2 in even rounds, decoded-tos2/decoded in odd rounds; source order rotated each round','engine':'auto','eligibility':'each Metadata optimized=none; genuine old VM required','step_limit_per_matrix':1000000000,'threads':4,'checks':'source, Metadata, input, cached original C outputs, oracle binary/harness and candidate SHA checked for each trial; complete file comparison afterward','preparation_cost':'per matrix decode is included in total compute; report summed vm_prepare_ms and peak retained vm_plan_bytes','default_promotion':False,'primary_refs':['https://www.lua.org/doc/sblp2005.pdf','https://www.lua.org/source/5.4/lvm.c.html','https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14'],'cases':[]}
    for source in proof['sources']:
        label=source['label'];folder=root/label;folder.mkdir();old=stage/'correctness'/label
        observed=next(r for r in proof['runs']if r['source']==label and r['family']=='dense' and r['backend']=='decoded')['vm_steps']
        repeats=math.ceil(plan['target_original_steps_per_trial']/observed)
        for name in ['source.c','program.meta','oracle.c','oracle.exe']:
            shutil.copyfile(old/name,folder/name)
        repeat_original_matrix_stream(old/'dense-input.bin',folder/'input.bin',repeats)
        repeat_original_matrix_stream(old/'dense-oracle.bin',folder/'oracle.bin',repeats)
        sizes=[3,11,67,139,193,257]if source['fresh']else[3,7,17,31,33,63,64,65,127,129]
        plan['cases'].append({'source':label,'function':source['analysis']['function'],'optimized':source['analysis']['optimized'],'fresh_holdout':source['fresh'],'sizes':sizes,'matrices':len(sizes)*repeats,'whole_stream_repeats':repeats,'original_steps':observed*repeats,'original_C_reference':'frozen previously executed GCC C oracle matrix bytes, repeated exactly; outer matrix-count only recomputed','cached_original_C_output_sha256':sha(old/'dense-oracle.bin'),'cached_original_input_sha256':sha(old/'dense-input.bin'),'hashes':{name:sha(folder/name)for name in ['source.c','program.meta','oracle.c','oracle.exe','input.bin','oracle.bin']}})
    assert len(plan['cases'])*plan['rounds']*2==plan['records']
    (root/'run-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps({'prepared':True,'records':plan['records'],'source_cases':len(plan['cases']),'plan':str(root/'run-plan.json')}),flush=True)
def run(project,root):
    plan=json.loads((root/'run-plan.json').read_text());assert not(root/'report.json').exists(),'never overwrite a prior performance run'
    assert sha(Path(__file__))==plan['script_sha256'];assert sha(project/'tools/windows_resource_probe.py')==plan['resource_probe_sha256'];runtime=root/'runtime.exe';assert sha(runtime)==plan['runtime_sha256']
    report={'passed':False,'status':'running','plan_sha256':sha(root/'run-plan.json'),'records':[],'summary':[],'default_promotion':False};began=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-began;(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    for repeat in range(plan['rounds']):
        cases=plan['cases'][repeat:]+plan['cases'][:repeat]
        for case in cases:
            folder=root/case['source']
            for backend in (('decoded','decoded-tos2')if repeat%2==0 else('decoded-tos2','decoded')):
                check=time.perf_counter();assert sha(runtime)==plan['runtime_sha256']
                for name,digest in case['hashes'].items():assert sha(folder/name)==digest,name
                validation_ms=(time.perf_counter()-check)*1000
                output=folder/f'round-{repeat}-{backend}.bin';command=[str(runtime),'--metadata',str(folder/'program.meta'),'--input',str(folder/'input.bin'),'--output',str(output),'--engine',plan['engine'],'--threads',str(plan['threads']),'--vm-step-limit',str(plan['step_limit_per_matrix']),'--vm-backend',backend]
                started=time.perf_counter();proc,resources=monitored_run(command);wall=(time.perf_counter()-started)*1000;metrics=json.loads(proc.stdout)
                assert metrics['selected_engine']=='vm' and metrics['vm_backend']==backend and metrics['vm_steps']==case['original_steps']
                check=time.perf_counter();match=exact_compare(folder/'oracle.bin',output);comparison_ms=(time.perf_counter()-check)*1000
                row={'source':case['source'],'round':repeat,'backend':backend,'source_sha256':case['hashes']['source.c'],'input_sha256':case['hashes']['input.bin'],'reference_sha256':case['hashes']['oracle.bin'],'sha_validation_ms':validation_ms,'whole_file_comparison_ms':comparison_ms,'process_wall_ms':wall,**resources,**metrics,**match};report['records'].append(row);save()
                print(json.dumps({'source':row['source'],'round':repeat,'backend':backend,'compute_ms':row['compute_ms'],'prepare_ms':row['vm_prepare_ms'],'byte_identical':True}),flush=True)
    for case in plan['cases']:
        rows=[r for r in report['records']if r['source']==case['source']];a=[r for r in rows if r['backend']=='decoded'];b=[r for r in rows if r['backend']=='decoded-tos2']
        ratios=[next(r for r in b if r['round']==i)['compute_ms']/next(r for r in a if r['round']==i)['compute_ms']for i in range(plan['rounds'])]
        report['summary'].append({'source':case['source'],'decoded_median_compute_ms':statistics.median(r['compute_ms']for r in a),'tos2_median_compute_ms':statistics.median(r['compute_ms']for r in b),'paired_compute_ratios':ratios,'median_paired_ratio':statistics.median(ratios),'tos2_compute_wins':sum(x<1 for x in ratios),'tos2_median_prepare_ms':statistics.median(r['vm_prepare_ms']for r in b),'plan_bytes_peak':max(r['vm_plan_bytes_peak']for r in b)})
    assert len(report['records'])==plan['records'];report.update(passed=True,status='complete');save();print(json.dumps({'passed':True,'records':len(report['records']),'seconds':report['elapsed_seconds']}),flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');args=ap.parse_args();project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-prepared-vm-phase2/performance'
    if args.prepare:prepare(project,root)
    else:run(project,root)
if __name__=='__main__':main()
