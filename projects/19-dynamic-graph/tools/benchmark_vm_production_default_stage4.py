"""Actual ordinary99a default versus historical4f73 default; prepare != run."""
import argparse,hashlib,json,shutil,statistics,struct,time
from pathlib import Path
from evaluate_source import exact_compare
from windows_resource_probe import monitored_run

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def headers(path):
    sizes=[]
    with path.open('rb')as f:
        raw=f.read(4);assert len(raw)==4;count=struct.unpack('<I',raw)[0]
        for _ in range(count):
            raw=f.read(4);assert len(raw)==4;n=struct.unpack('<I',raw)[0]
            assert 3<=n<=10000;sizes.append(n);f.seek(8*n*n,1)
        assert f.tell()==path.stat().st_size and f.read()==b''
    return sizes
def prepare(p,root):
    stage=p/'artifacts/stage2-vm-default-integration';oldperf=p/'artifacts/stage2-prepared-vm-phase3/performance';prior=read(oldperf/'run-plan.json');released=read(stage/'ordinary-install/release-manifest.json')
    assert released['passed']and released['runtime_sha256']==sha(p/'build/cholesky_runtime.exe')
    root.mkdir(exist_ok=False)
    shutil.copyfile(Path(__file__),root/'benchmark-script.py');shutil.copyfile(p/'tools/windows_resource_probe.py',root/'windows_resource_probe.py')
    executables={'old-default':stage/'rollback4f73/cholesky_runtime.exe','new-default':p/'build/cholesky_runtime.exe'}
    expected={'old-default':released['ordinary_rollback_sha256'],'new-default':released['runtime_sha256']}
    bins={}
    for name,exe in executables.items():
        assert sha(exe)==expected[name];dest=root/(name+'.exe');shutil.copyfile(exe,dest);bins[name]={'path':str(dest),'sha256':sha(dest)}
    for label,source,build in [('old',stage/'rollback4f73/released-source',stage/'rollback4f73/released-build'),('new',stage/'ordinary-install/released-source',stage/'ordinary-install/released-build')]:
        shutil.copytree(source,root/'source-frozen'/label/'source');shutil.copytree(build,root/'source-frozen'/label/'build')
    source_hashes={x.relative_to(root/'source-frozen').as_posix():sha(x)for x in sorted((root/'source-frozen').rglob('*'))if x.is_file()}
    plan={'status':'predeclared; no performance started','version':1,'scope':'actual installed ordinary99a default versus frozen ordinary4f73 default; full thirteen VM-required source cohort; no claim for native Cholesky or official85 points','binaries':bins,'source_snapshot_sha256':source_hashes,'script_sha256':sha(root/'benchmark-script.py'),'resource_probe_sha256':sha(root/'windows_resource_probe.py'),'ordinary_release_manifest_sha256':sha(stage/'ordinary-install/release-manifest.json'),'phase3_cohort_plan_sha256':sha(oldperf/'run-plan.json'),'records':130,'pairs':65,'rounds':5,'engine':'auto','threads':4,'CLI_backend_override':False,'CLI_budget_override':False,'both_default_budget':1000000000,'pair_order':'old/new on even rounds; new/old on odd rounds; source list rotated by round','same_cached_C_repetition':True,'new_oracle_execution':False,'timing_based_case_selection':False,'preparation_cost':'new reported vm_prepare_ms is included in compute; old EXE has no vm_steps/vm_prepare fields, retain absent rather than populate','host_resources':'actual PeakWS/commit/freeRAM/hostCPU each trial; project jobs isolated, user background apps untouched; no assertion of whole host idle','external_costs':'SHA and complete reference comparison timed separately from process wall; input/output/metadata IO retained from raw metrics','primary_refs':prior['primary_refs'],'cases':[]}
    for case in prior['cases']:
        label=case['source'];folder=root/label;folder.mkdir();previous=oldperf/label
        for name,digest in case['hashes'].items():
            assert sha(previous/name)==digest;shutil.copyfile(previous/name,folder/name);assert sha(folder/name)==digest
        sizes=headers(folder/'input.bin');assert sizes==case['sizes']*case['whole_stream_repeats']and headers(folder/'oracle.bin')==sizes
        assert (folder/'program.meta').read_text(encoding='utf-8').split('PROGRAM\n')[0].splitlines().count('optimized=none')==1
        item=dict(case);item.update(previous_phase3_fresh_source=case['fresh_source'],previous_phase3_fresh_shape=case['fresh_shape'],fresh_source=False,fresh_shape=False,reused_frozen_cohort=True,input_matrix_headers=sizes,header_matrix_count=len(sizes),expected_new_reported_steps=case['original_steps'],old_reported_steps_expected_absent=True)
        plan['cases'].append(item)
    assert len(plan['cases'])==13 and plan['records']==len(plan['cases'])*plan['rounds']*2
    (root/'run-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(json.dumps({'prepared':True,'records':130,'pairs':65,'cases':13,'plan_sha256':sha(root/'run-plan.json'),'binaries':bins,'frozen_source_files':len(source_hashes),'performance_started':False},indent=2),flush=True)
def run(p,root):
    plan=read(root/'run-plan.json');assert not(root/'report.json').exists(),'no restart/overwrite of observed trials'
    assert sha(Path(__file__))==plan['script_sha256']and sha(p/'tools/windows_resource_probe.py')==plan['resource_probe_sha256']
    for binary in plan['binaries'].values():assert sha(Path(binary['path']))==binary['sha256']
    report={'passed':False,'status':'running','plan_sha256':sha(root/'run-plan.json'),'records':[],'summary':[],'scope':plan['scope'],'new_default_installed_before_trial':True,'runtime_or_budget_changed':False};began=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-began;(root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    for round in range(plan['rounds']):
        cases=plan['cases'][round:]+plan['cases'][:round]
        for case in cases:
            folder=root/case['source']
            for backend in (('old-default','new-default')if round%2==0 else('new-default','old-default')):
                check=time.perf_counter();binary=plan['binaries'][backend];exe=Path(binary['path']);assert sha(exe)==binary['sha256']
                for name,digest in case['hashes'].items():assert sha(folder/name)==digest,name
                assert headers(folder/'input.bin')==case['input_matrix_headers']and headers(folder/'oracle.bin')==case['input_matrix_headers']
                sha_ms=(time.perf_counter()-check)*1000
                output=folder/f'round-{round}-{backend}.bin';cmd=[str(exe),'--metadata',str(folder/'program.meta'),'--input',str(folder/'input.bin'),'--output',str(output),'--engine',plan['engine'],'--threads',str(plan['threads'])]
                start=time.perf_counter();proc,resources=monitored_run(cmd);wall_ms=(time.perf_counter()-start)*1000
                (folder/f'round-{round}-{backend}.stdout').write_text(proc.stdout,encoding='utf-8');(folder/f'round-{round}-{backend}.stderr').write_text(proc.stderr,encoding='utf-8')
                metrics=json.loads(proc.stdout);assert metrics['selected_engine']=='vm'and metrics['matrices']==case['matrices']
                if backend=='new-default':assert metrics['vm_backend']=='decoded-threaded'and metrics['vm_steps']==case['expected_new_reported_steps']and 0<=metrics['vm_prepare_ms']<=metrics['compute_ms']
                else:assert not any(name in metrics for name in ['vm_backend','vm_steps','vm_prepare_ms','vm_plan_bytes_peak'])
                start=time.perf_counter();match=exact_compare(folder/'oracle.bin',output);compare_ms=(time.perf_counter()-start)*1000
                row={'source':case['source'],'round':round,'backend':backend,'command':cmd,'actual_exit_code':proc.returncode,'exe_sha256':binary['sha256'],'source_sha256':case['hashes']['source.c'],'metadata_sha256':case['hashes']['program.meta'],'input':str(folder/'input.bin'),'input_sha256':case['hashes']['input.bin'],'reference':str(folder/'oracle.bin'),'reference_sha256':case['hashes']['oracle.bin'],'output':str(output),'sha_validation_ms':sha_ms,'whole_file_comparison_ms':compare_ms,'process_wall_ms':wall_ms,'old_unreported_VM_counters_not_invented':backend=='old-default',**resources,**metrics,**match};report['records'].append(row);save()
                print(json.dumps({'source':case['source'],'round':round,'backend':backend,'compute_ms':metrics['compute_ms'],'reported_prepare_ms':metrics.get('vm_prepare_ms'),'byte_identical':True}),flush=True)
    pairs=[]
    for case in plan['cases']:
        rows=[r for r in report['records']if r['source']==case['source']]
        old=[r for r in rows if r['backend']=='old-default'];new=[r for r in rows if r['backend']=='new-default'];ratios=[];wall=[]
        for round in range(plan['rounds']):
            a=next(r for r in old if r['round']==round);b=next(r for r in new if r['round']==round)
            ratio=b['compute_ms']/a['compute_ms'];wr=b['process_wall_ms']/a['process_wall_ms'];ratios.append(ratio);wall.append(wr)
            pairs.append({'source':case['source'],'round':round,'compute_ratio_new_over_old':ratio,'wall_ratio_new_over_old':wr,'compute_outcome':'win'if ratio<1 else'tie'if ratio==1 else'negative'})
        report['summary'].append({'source':case['source'],'old_default_median_compute_ms':statistics.median(r['compute_ms']for r in old),'new_default_median_compute_ms':statistics.median(r['compute_ms']for r in new),'paired_compute_ratios':ratios,'paired_wall_ratios':wall,'median_paired_ratio':statistics.median(ratios),'median_paired_wall_ratio':statistics.median(wall),'new_default_compute_wins':sum(x<1 for x in ratios),'new_default_compute_negatives':sum(x>1 for x in ratios),'new_default_median_prepare_ms':statistics.median(r['vm_prepare_ms']for r in new),'old_prepare_counter_absent':True,'new_plan_bytes_peak':max(r['vm_plan_bytes_peak']for r in new),'median_input_read_ms_old':statistics.median(r['input_read_ms']for r in old),'median_input_read_ms_new':statistics.median(r['input_read_ms']for r in new),'median_output_write_ms_old':statistics.median(r['output_write_ms']for r in old),'median_output_write_ms_new':statistics.median(r['output_write_ms']for r in new)})
    assert len(report['records'])==plan['records']and len(pairs)==plan['pairs']
    report.update(passed=True,status='complete',pairs=pairs,pair_count=len(pairs),wins=sum(x['compute_outcome']=='win'for x in pairs),negative_pairs=[x for x in pairs if x['compute_outcome']=='negative'],ties=sum(x['compute_outcome']=='tie'for x in pairs));save()
    print(json.dumps({'passed':True,'records':130,'pairs':65,'wins':report['wins'],'negative_pairs':len(report['negative_pairs']),'ties':report['ties'],'seconds':report['elapsed_seconds']}),flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');args=ap.parse_args();p=Path(__file__).resolve().parents[1];root=p/'artifacts/stage2-vm-default-integration/production-performance'
    if args.prepare:prepare(p,root)
    else:run(p,root)
if __name__=='__main__':main()
