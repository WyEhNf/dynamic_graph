"""Static full-real-C and matched-binary cost plan; no compiler/C/VM/test run."""
import copy,hashlib,json,re,shutil,struct
from pathlib import Path
P=Path(__file__).resolve().parents[1]
R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
D=P/'artifacts/stage2-vm-nested-budget/execution-static-design-v2'
H=P/'artifacts/stage2-vm-nested-budget/policy-cost'
OUT=R/'next-static-plan'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def headers(path):
    result=[]
    with path.open('rb')as f:
        count=struct.unpack('<I',f.read(4))[0]
        for _ in range(count):
            n=struct.unpack('<I',f.read(4))[0];assert 3<=n<=10000;result.append(n);f.seek(n*n*8,1)
        assert f.tell()==path.stat().st_size
    return result
def instructions(name):
    text=(OUT/(name+'-mangled.asm')).read_text(encoding='utf-8-sig')
    result=[]
    for line in text.splitlines():
        m=re.match(r'\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*\t(.*)',line)
        if m:result.append({'address':int(m[1],16),'bytes':len(m[2].split()),'asm':m[3]})
    assert len(result)>1000
    return result
def targets(name):
    data=b''
    for line in (OUT/(name+'-targets.txt')).read_text(encoding='utf-8-sig').splitlines():
        m=re.match(r'\s+[0-9a-f]+\s+((?:[0-9a-f]{8}\s+){1,4})',line)
        if m:data+=bytes.fromhex(m[1])
    assert len(data)==264
    return list(struct.unpack('<33Q',data))
def main():
    assert not (OUT/'plan.json').exists()
    accepted=read(R/'build-gate-acceptance/manifest.json');assert accepted['passed']
    prior=read(H/'run-plan.json');design=read(D/'plan.json')
    sources=design['sources'];assert len(sources)==19
    program_names={s['source']for s in sources};source_labels={s['source_label']for s in sources}
    chosen=[copy.deepcopy(c)for c in prior['cases']if c['source']in program_names or c['source'].removesuffix('-signedzero')in source_labels]
    assert len(chosen)==25 and len({c['hashes']['source.c']for c in chosen})==19
    for c in chosen:
        label=c['source'];dest=OUT/'references'/label;dest.mkdir(parents=True)
        c['declared_original_C_hashes']=copy.deepcopy(c['hashes'])
        c['input_header_observation']=headers(Path(c['paths']['input.bin']));assert c['input_header_observation']==c['input_matrix_headers']
        assert Path(c['paths']['oracle.bin']).stat().st_size==c['reference_bytes']
        c['external_data_SHA_status']='inherited independently accepted exact originalC SHA; only size/headers read now; all source/input/oracle SHA freshly required in future authorized execution'
        for name in ['source.c','program.meta','oracle.c','oracle.exe']:
            original=Path(c['paths'][name]);assert sha(original)==c['hashes'][name]
            shutil.copyfile(original,dest/name);c['paths'][name]=str(dest/name)
        c['scope']='original13 unchanged historical repeat stream'if label in [s['source']for s in sources[:13]]else 'actual six C holdouts, original unamplified5 shapes/family; not newly generated'
        c['expected_exitcode']=0
        c['default_path_scope']='native-control'if c['kind']=='native'else 'genuine-default-VM'
    forced=[]
    for c in chosen:
        if c['source'].startswith('strict-cholesky-control-'):
            new=copy.deepcopy(c);new['identity']=new['source']+'-forced-vm';new['engine_requested']='vm'
            new['expected_vm_steps']=None;new['default_path_scope']='forced-VM diagnostic, excluded from default benefit aggregate'
            forced.append(new)
    assert len(forced)==2
    perf=[copy.deepcopy(c)for c in chosen if c['source']in program_names]
    assert len(perf)==19 and sum(c['kind']=='vm'for c in perf)==18
    for c in chosen:c['identity']=c['source']
    for c in perf:c['identity']=c['source']
    for c in chosen+forced+perf:
        c['backends']=['decoded-threaded','decoded-threaded-load-pair']
        c['runtime_command_common']=[str(R/'build-gate-acceptance/build-gnu/cholesky_runtime.exe'),
                                     '--metadata',c['paths']['program.meta'],'--input',c['paths']['input.bin'],
                                     '--engine',c['engine_requested'],'--scheduler',prior['scheduler'],
                                     '--threads',str(prior['threads']),'--block-size',str(c['block']),'--vm-budget','fixed']
    asm={}
    for name in ['threaded','load-pair']:
        ops=instructions(name);ts=targets(name)
        asm[name]={'start':hex(ops[0]['address']),'last_instruction_end':hex(ops[-1]['address']+ops[-1]['bytes']),
                   'approximate_function_bytes':ops[-1]['address']+ops[-1]['bytes']-ops[0]['address'],
                   'parsed_instruction_lines':len(ops),'LOAD_target':hex(ts[1]),
                   'all33_targets':[hex(v)for v in ts],
                   'indirect_jump_sites':[hex(o['address'])for o in ops if re.search(r'^jmp\s+\*',o['asm'])]}
    newops=instructions('load-pair');path=[o for o in newops if 0x14001fb30<=o['address']<=0x14001fc46]
    assert len(asm['threaded']['indirect_jump_sites'])==len(asm['load-pair']['indirect_jump_sites'])==3
    assert not any(re.search(r'^jmp\s+\*',o['asm'])for o in path)
    asm['candidate_hot_pair_path']=[{'address':hex(o['address']),'asm':o['asm']}for o in path]
    asm['observation']='Three static indirect sites each, GCC merged dispatch tails. Successful LOAD pair uses one initial indirect dispatch then two pushes/check boundaries with no intermediate indirectjmp. Discovery/bitmap branch/code size and knownLOAD field-copy optimizations remain confounders; no speedup claim.'
    asm['first_extraction_preserved']='Initial -C plus mangled --disassemble returned empty body despite exit0; threaded.asm/load-pair.asm retained. Corrected no-C outputs separate *-mangled.asm; no candidate or flags change.'
    write(OUT/'machine-code-observation.json',asm)
    plan={'schema':'load-pair-realC-and-matched-cost-static-plan-v1','status':'prepared only; no VM/C/compiler/functional/performance execution',
          'accepted_gate_manifest_sha256':sha(R/'build-gate-acceptance/manifest.json'),
          'static_CFG_design_sha256':sha(D/'plan.json'),'original_C_lineage_plan_sha256':sha(H/'run-plan.json'),
          'runtime':{'path':str(R/'build-gate-acceptance/build-gnu/cholesky_runtime.exe'),
                     'sha256':sha(R/'build-gate-acceptance/build-gnu/cholesky_runtime.exe'),
                     'core_sha256':sha(R/'build-gate-acceptance/build-gnu/libcholesky_core.a'),
                     'header_sha256':sha(R/'workspace/include/cholesky/runtime.hpp'),
                     'core_flags_sha256':sha(R/'build-gate-acceptance/build-gnu/CMakeFiles/cholesky_core.dir/flags.make')},
          'source_counts':{'old_true_VM_sources':13,'fresh_C_sources':6,'all_unique_actual_C_sources':19},
          'functional':{'cached_C_streams':25,'two_backends_records':50,'forced_strict_C_VM_diagnostic_streams':2,'forced_diagnostic_records':4,
                        'total_runtime_records':54,'cases':chosen,'forced_cases':forced,
                        'no_new_AST_IR_C_oracles_required':True,'complete_C_output_bytes_compare':True,
                        'exact_same_steps_and_lastpc_required_between_VM_backends':True,'first_failure_preserved_stop_no_retry':True},
          'cost':{'cases':perf,'rounds':5,'records':190,'pairs':95,'genuine_VM_pairs':90,'native_bypass_control_pairs':5,
                  'alternating_order':'case-major round1 plain/fused, round2 fused/plain, round3 plain/fused, round4 fused/plain, round5 plain/fused',
                  'sole_variation':'explicit VM backend; same actuala95 EXE/fixed default1e9/no proof/cache/N routing',
                  'not_99a_or_844_gain_comparison':True,'no_new_repetition_or_amplification':True,
                  'retained_failures_and_negative_pairs':True,'small_task_negative_and_launch_noise_remain':True,
                  'defaultVM_and_native_control_aggregates_separate':True,'forced_native_VM_excluded_from_performance':True,
                  'original_C_whole_bytes_each_trial':True,
                  'measurements':['reported compute (includes decode/discovery)','vm_prepare_ms','fusionplan ms/residentbytes/pairs discovered/executed',
                                  'vm steps/lastpc/engine/backend','input_validation_ms','read_ms','write_ms','external processwall',
                                  'separate SHA/wholebytes validation wall','fresh RAM/disk','actual process PeakWS/commit/CPU','raw host background busy/RAM'],
                  'host_not_claimed_idle_user_apps_untouched':True},
          'guards':{'fixed_budget_default':1000000000,'no_explicit_limit':'intentionally omitted; no proved acceptance here',
                    'fresh_RAM_and_G_each_launch_bytes':1073741824,'failure_resource_exit':75,'file_stdio':'frozen Win32 file-backed helper',
                    'TEMP_TMP_TMPDIR':str(R/'compiler-temp'),'no_autorestart_or_remove_old_artifacts':True,
                    'no_execution_until_parent_separate_functional_and_performance_authorization':True},
          'source_behavior':'Metadata/PROGRAM full exact original fields; fusion from fullCFG only, no source/hash/N routing; errors unused delayed and all33 steps/PC preserved.',
          'evidence_limits':'Prior 41CTest default-auto C pipelines verify overall compatibility. New8464+934 and CLI verify small fusion contracts only; full19 actualC fused correctness and paired compute still pending.',
          'data_budget':{'functional_output_bytes_estimate':sum(c['reference_bytes']for c in chosen+forced)*2,
                         'performance_output_bytes_estimate':sum(c['reference_bytes']for c in perf)*10,
                         'all_reserved_on_G':True},
          'machine_code_observation_sha256':sha(OUT/'machine-code-observation.json'),
          'ordinary_sha256':sha(P/'build/cholesky_runtime.exe'),'memory_sha256':sha(P/'build-memory/cholesky_runtime.exe')}
    write(OUT/'plan.json',plan)
    shutil.copyfile(Path(__file__),OUT/'producer.py')
    frozen={p.relative_to(OUT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(OUT.rglob('*'))if p.is_file()}
    write(OUT/'manifest.json',{'schema':'load-pair-static-next-plan-freeze-v1','files':frozen})
    print(json.dumps({'prepared_only':True,'plan_sha256':sha(OUT/'plan.json'),'manifest_sha256':sha(OUT/'manifest.json'),
                      'frozen_files':len(frozen),'functional_records':54,'cost_records':190,'cost_pairs':95,
                      'data_budget':plan['data_budget']}),flush=True)
if __name__=='__main__':main()
