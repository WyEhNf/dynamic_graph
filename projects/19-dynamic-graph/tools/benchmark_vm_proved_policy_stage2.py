"""Predeclared same-binary fixed/proved costs; preparation never executes C/VM."""
import argparse,ctypes,hashlib,json,os,re,shutil,statistics,struct,time
from pathlib import Path
from evaluate_source import exact_compare
from windows_resource_probe import HostMemory,monitored_run
P=Path(__file__).resolve().parents[1];STAGE=P/'artifacts/stage2-vm-proved-budget';ROOT=STAGE/'policy-cost';ACCEPT=STAGE/'runtime-integration/acceptance'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def headers(path):
    sizes=[]
    with Path(path).open('rb')as stream:
        count=struct.unpack('<I',stream.read(4))[0]
        for _ in range(count):
            n=struct.unpack('<I',stream.read(4))[0];assert 3<=n<=10000;sizes.append(n);stream.seek(8*n*n,1)
        assert stream.tell()==Path(path).stat().st_size and stream.read()==b''
    return sizes
def available():
    value=HostMemory();value.dwLength=ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):raise ctypes.WinError()
    return value.ullAvailPhys
def prepare():
    accepted=read(ACCEPT/'manifest.json');assert accepted['passed'];ROOT.mkdir(exist_ok=False)
    assert sha(P/'build/cholesky_runtime.exe')==accepted['ordinary_sha256']
    old=P/'artifacts/stage2-prepared-vm-phase3/performance';prior=read(old/'run-plan.json');functional=read(STAGE/'runtime-integration/correctness/report.json')
    exe=ACCEPT/'gnu/cholesky_runtime.exe';assert sha(exe)==accepted['binaries']['gnu']['cholesky_runtime.exe']['sha256'];shutil.copyfile(exe,ROOT/'runtime.exe')
    shutil.copytree(ACCEPT/'source',ROOT/'implementation-source');shutil.copytree(ACCEPT/'gnu/build-provenance',ROOT/'implementation-build')
    source_hashes={x.relative_to(ROOT).as_posix():sha(x)for folder in ['implementation-source','implementation-build']for x in sorted((ROOT/folder).rglob('*'))if x.is_file()}
    for x in [Path(__file__),P/'tools/windows_resource_probe.py',P/'tools/evaluate_source.py',P/'docs/stage2-vm-proved-policy-cost-plan.md',P/'docs/stage2-vm-nested-budget-design.md']:
        dest=ROOT/'plan-source'/x.relative_to(P);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,dest);source_hashes[dest.relative_to(ROOT).as_posix()]=sha(dest)
    cases=[]
    def add(label,kind,paths,expected_hashes,engine='auto',block=7,expected_steps=None,expected_status=None,lineage=None):
        folder=ROOT/label;folder.mkdir();digests={}
        for name,source in paths.items():
            assert sha(source)==expected_hashes[name],(label,name);shutil.copyfile(source,folder/name);digests[name]=sha(folder/name)
        sizes=headers(folder/'input.bin');assert headers(folder/'oracle.bin')==sizes
        text=(folder/'program.meta').read_text(encoding='utf-8');optimized=re.search(r'^optimized=(.+)$',text,re.MULTILINE)[1]
        if kind=='vm':assert optimized=='none'
        else:assert optimized in ['scalar_cholesky_column_dag','rightlooking_cholesky_column_dag','rightlooking_cholesky_column_dag_fma']
        cases.append({'source':label,'kind':kind,'hashes':digests,'engine_requested':engine,'block':block,'input_matrix_headers':sizes,'matrices':len(sizes),'optimized':optimized,'expected_vm_steps':expected_steps,'expected_proof_status':expected_status,'lineage':lineage,'reference_bytes':(folder/'oracle.bin').stat().st_size})
    for case in prior['cases']:
        label=case['source'];paths={name:old/label/name for name in case['hashes']}
        summary=next(s for s in accepted['proof_status_by_source']if s['source']==label);status='proved'if summary['proved_matrices']else'unknown'
        add(label,'vm',paths,case['hashes'],block=32,expected_steps=case['original_steps'],expected_status=status,lineage={'prior_plan':str(old/'run-plan.json'),'whole_stream_repeats':case['whole_stream_repeats'],'scope':'exact previous performance stream; not a new source or shape'})
    for label in ['heldout-stride2','heldout-disjoint']:
        source=next(s for s in functional['sources']if s['label']==label);row=next(r for r in functional['runs']if r['source']==label and r['family']=='dense'and r['mode']=='fixed-auto');folder=Path(source['folder'])
        paths={'source.c':folder/'source.c','program.meta':folder/'program.meta','oracle.c':folder/'oracle.c','oracle.exe':folder/'oracle.exe','input.bin':Path(row['input']),'oracle.bin':Path(row['reference'])}
        expected={name:sha(x)for name,x in paths.items()};assert expected['source.c']==source['source_sha256']and expected['program.meta']==source['metadata_sha256']and expected['input.bin']==row['input_sha256']and expected['oracle.bin']==row['reference_sha256']
        add(label,'vm',paths,expected,block=32,expected_steps=row['vm_steps'],expected_status='proved',lineage={'functional_report':str(STAGE/'runtime-integration/correctness/report.json'),'whole_stream_repeats':1,'scope':'unamplified dense short-task batch; shapes unchanged7/13/29/53'})
    wire=P/'artifacts/stage2-runtime-release/wire';wire_report=read(wire/'report.json');assert wire_report['passed']
    controls=[('control-scalar-auto-dense','scalar','dense','auto'),('control-scalar-auto-diagonal','scalar','diagonal-signed-zero','auto'),('control-page-tiled-dense','page','dense','tiled'),('control-blocked-auto-dense','blocked','dense','auto')]
    for label,name,family,engine in controls:
        source=next(s for s in wire_report['sources']if s['label']==name);fmt=next(f for f in source['formats']if f['schema']==2 and f['mode']=='dag');row=next(r for r in fmt['runs']if r['family']==family and r['engine']=='tiled');folder=wire/name
        cfile=folder/'source.c'
        if not cfile.exists():cfile=Path(re.search(r'^#include "([^"]+)"',(folder/'oracle.c').read_text(),re.MULTILINE)[1])
        paths={'source.c':cfile,'program.meta':folder/'schema2-dag.meta','oracle.c':folder/'oracle.c','oracle.exe':folder/'oracle.exe','input.bin':folder/(family+'-input.bin'),'oracle.bin':folder/(family+'-oracle.bin')}
        expected={key:sha(x)for key,x in paths.items()};assert expected['source.c']==source['source_sha256']and expected['program.meta']==fmt['sha256']and expected['oracle.bin']==row['sha256']
        add(label,'native',paths,expected,engine=engine,block=7,expected_steps=0,expected_status='not-run',lineage={'wire_report':str(wire/'report.json'),'source':name,'family':family,'reference_note':'actual independently compiled source at block7; original flagsgcc O2 fno-fast-math ffp-contract=off','expected_engine':'diagonal'if family=='diagonal-signed-zero'else'tiled'if engine=='tiled'else'auto stage/tiled according to actual last shape'})
    assert len(cases)==19 and sum(x['kind']=='vm'for x in cases)==15
    plan={'status':'predeclared; no performance started','version':1,'scope':'same acceptedb9 binary fixed/proved policy overhead; prospective default assessment, no installed/default change','binary':{'path':str(ROOT/'runtime.exe'),'sha256':sha(ROOT/'runtime.exe')},'acceptance_manifest_sha256':sha(ACCEPT/'manifest.json'),'source_snapshot_sha256':source_hashes,'cases':cases,'records':114,'pairs':57,'VM_records':90,'VM_pairs':45,'native_control_records':24,'native_control_pairs':12,'rounds':3,'pair_order':'fixed/proved in even rounds; proved/fixed in odd rounds; rotate19-case list by round','threads':4,'scheduler':'parallel','sole_command_variation':'--vm-budget fixed versus proved','literal_step_limit':None,'backend_override':None,'same_program_and_metadata':True,'proof_and_decode_in_compute':True,'new_C_execution':False,'timing_based_case_selection':False,'small_batch_minimum_launch_RAM_bytes':268435456,'minimum_disk_overhead_bytes':268435456,'expected_output_bytes_total':sum(x['reference_bytes']for x in cases)*6,'preserve_all_unknown_and_negative':True,'user_apps_untouched':True,'host_not_claimed_idle':True,'ordinary_sha256':accepted['ordinary_sha256'],'memory_sha256':accepted['memory_sha256'],'native_FLAG_provenance':'implementation-build frozen exactaccepted GNU flags/CMakeCache/link; source/harness/oracle C hashes in every case','prepare_free_F_bytes':shutil.disk_usage(ROOT).free,'prepare_available_RAM_bytes':available(),'primary_refs':['https://llvm.org/docs/LoopTerminology.html','https://llvm.org/doxygen/classllvm_1_1ScalarEvolution.html']}
    (ROOT/'run-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps({'prepared':True,'records':114,'pairs':57,'cases':19,'plan_sha256':sha(ROOT/'run-plan.json'),'output_bytes_planned':plan['expected_output_bytes_total'],'available_RAM_bytes':plan['prepare_available_RAM_bytes'],'free_F_bytes':plan['prepare_free_F_bytes'],'performance_started':False}),flush=True)
def run():
    plan=read(ROOT/'run-plan.json');assert not(ROOT/'report.json').exists(),'never restart/overwrite an observed batch'
    assert sha(ACCEPT/'manifest.json')==plan['acceptance_manifest_sha256']and sha(plan['binary']['path'])==plan['binary']['sha256']
    for relative,digest in plan['source_snapshot_sha256'].items():assert sha(ROOT/relative)==digest
    for relative in ['tools/benchmark_vm_proved_policy_stage2.py','tools/windows_resource_probe.py','tools/evaluate_source.py']:assert sha(P/relative)==plan['source_snapshot_sha256']['plan-source/'+relative]
    report={'passed':False,'status':'running','plan_sha256':sha(ROOT/'run-plan.json'),'records':[],'summary':[],'resource_gates':[],'source_or_binary_changed':False,'ordinary_default_promoted':False};began=time.perf_counter()
    def save():report['elapsed_seconds']=time.perf_counter()-began;(ROOT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    for round in range(plan['rounds']):
        cases=plan['cases'][round:]+plan['cases'][:round]
        for case in cases:
            folder=ROOT/case['source']
            for mode in (['fixed','proved']if round%2==0 else['proved','fixed']):
                checked=time.perf_counter();assert sha(plan['binary']['path'])==plan['binary']['sha256']
                for name,digest in case['hashes'].items():assert sha(folder/name)==digest
                assert headers(folder/'input.bin')==headers(folder/'oracle.bin')==case['input_matrix_headers'];sha_ms=(time.perf_counter()-checked)*1000
                ram_before=available();disk=shutil.disk_usage(ROOT).free;remaining=plan['expected_output_bytes_total']-sum(r['bytes']for r in report['records'])+plan['minimum_disk_overhead_bytes'];good=ram_before>=plan['small_batch_minimum_launch_RAM_bytes']and disk>=remaining
                report['resource_gates'].append({'source':case['source'],'round':round,'mode':mode,'available_RAM_bytes':ram_before,'free_F_bytes':disk,'minimum_remaining_disk_bytes':remaining,'passed':good});save()
                if not good:report.update(status='resource-gate-blocked',pending={'source':case['source'],'round':round,'mode':mode});save();raise SystemExit(75)
                output=folder/f'round-{round}-{mode}.bin';assert not output.exists();command=[plan['binary']['path'],'--metadata',str(folder/'program.meta'),'--input',str(folder/'input.bin'),'--output',str(output),'--engine',case['engine_requested'],'--threads',str(plan['threads']),'--scheduler',plan['scheduler'],'--block-size',str(case['block']),'--vm-budget',mode]
                started=time.perf_counter();proc,resources=monitored_run(command,check=False);wall_ms=(time.perf_counter()-started)*1000
                (folder/f'round-{round}-{mode}.stdout').write_text(proc.stdout,encoding='utf-8');(folder/f'round-{round}-{mode}.stderr').write_text(proc.stderr,encoding='utf-8');assert proc.returncode==0,proc.stderr
                metrics=json.loads(proc.stdout);assert metrics['matrices']==case['matrices']and metrics['vm_budget_mode']==mode
                assert 0<=metrics['vm_budget_proof_ms']<=metrics['compute_ms']and 0<=metrics['vm_prepare_ms']<=metrics['compute_ms']
                if case['kind']=='vm':
                    assert metrics['selected_engine']=='vm'and metrics['vm_backend']=='decoded-threaded'and metrics['vm_steps']==case['expected_vm_steps']and metrics['vm_effective_step_limit_max']==1000000000
                    if mode=='fixed':assert metrics['vm_budget_proof_ms']==0 and metrics['vm_budget_work']==0 and metrics['vm_budget_proved_matrices']==metrics['vm_budget_unknown_matrices']==metrics['vm_budget_not_run_matrices']==0
                    else:
                        assert metrics['vm_budget_proved_matrices']+metrics['vm_budget_unknown_matrices']==case['matrices']and metrics['vm_budget_not_run_matrices']==0
                        assert metrics['vm_budget_proved_matrices'if case['expected_proof_status']=='proved'else'vm_budget_unknown_matrices']==case['matrices']
                else:
                    assert metrics['selected_engine']in ['stage','tiled','diagonal']and metrics['vm_backend']==''and metrics['vm_steps']==0 and metrics['vm_effective_step_limit_max']==0
                    assert metrics['vm_budget_proof_ms']==0 and metrics['vm_budget_work']==0 and metrics['vm_budget_bound_peak']==0 and metrics['vm_budget_not_run_matrices']==case['matrices']
                    assert metrics['vm_budget_proved_matrices']==metrics['vm_budget_unknown_matrices']==0
                    if case['lineage']['expected_engine']=='diagonal':assert metrics['selected_engine']=='diagonal'
                    elif case['engine_requested']=='tiled':assert metrics['selected_engine']=='tiled'
                started=time.perf_counter();match=exact_compare(folder/'oracle.bin',output);comparison_ms=(time.perf_counter()-started)*1000;assert match['bytes']==case['reference_bytes']
                row={'source':case['source'],'kind':case['kind'],'round':round,'mode':mode,'command':command,'actual_exit_code':proc.returncode,'exe_sha256':plan['binary']['sha256'],'case_hashes':case['hashes'],'input':str(folder/'input.bin'),'reference':str(folder/'oracle.bin'),'output':str(output),'sha_validation_ms':sha_ms,'whole_file_comparison_ms':comparison_ms,'process_wall_ms':wall_ms,'available_RAM_before_bytes':ram_before,**metrics,**resources,**match};report['records'].append(row);save();print(json.dumps({'source':case['source'],'kind':case['kind'],'round':round,'mode':mode,'compute_ms':metrics['compute_ms'],'proof_ms':metrics['vm_budget_proof_ms'],'proved':metrics['vm_budget_proved_matrices'],'unknown':metrics['vm_budget_unknown_matrices'],'actual_engine':metrics['selected_engine'],'byte_identical':True}),flush=True)
    pairs=[]
    for case in plan['cases']:
        rows=[r for r in report['records']if r['source']==case['source']];ratios=[];wall=[]
        for round in range(plan['rounds']):
            fixed=next(r for r in rows if r['round']==round and r['mode']=='fixed');proved=next(r for r in rows if r['round']==round and r['mode']=='proved');ratio=proved['compute_ms']/fixed['compute_ms'];wr=proved['process_wall_ms']/fixed['process_wall_ms'];ratios.append(ratio);wall.append(wr)
            pairs.append({'source':case['source'],'kind':case['kind'],'round':round,'compute_ratio_proved_over_fixed':ratio,'compute_delta_ms':proved['compute_ms']-fixed['compute_ms'],'wall_ratio_proved_over_fixed':wr,'outcome':'win'if ratio<1 else'tie'if ratio==1 else'negative'})
        report['summary'].append({'source':case['source'],'kind':case['kind'],'paired_compute_ratios':ratios,'paired_wall_ratios':wall,'median_paired_compute_ratio':statistics.median(ratios),'median_paired_wall_ratio':statistics.median(wall),'fixed_median_compute_ms':statistics.median(r['compute_ms']for r in rows if r['mode']=='fixed'),'proved_median_compute_ms':statistics.median(r['compute_ms']for r in rows if r['mode']=='proved'),'median_proof_ms':statistics.median(r['vm_budget_proof_ms']for r in rows if r['mode']=='proved'),'wins':sum(x<1 for x in ratios),'negative':sum(x>1 for x in ratios)})
    assert len(report['records'])==plan['records']and len(pairs)==plan['pairs'];report.update(passed=True,status='complete',pairs=pairs,VM_pairs=sum(x['kind']=='vm'for x in pairs),native_pairs=sum(x['kind']=='native'for x in pairs),negative_pairs=[x for x in pairs if x['outcome']=='negative']);save();print(json.dumps({'passed':True,'records':len(report['records']),'pairs':len(pairs),'negative_pairs':len(report['negative_pairs']),'report_sha256':sha(ROOT/'report.json')}),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args();temp=STAGE/'compiler-temp';temp.mkdir(exist_ok=True);os.environ.update({k:str(temp)for k in ['TEMP','TMP','TMPDIR']})
    if args.prepare:prepare()
    else:run()
if __name__=='__main__':main()
