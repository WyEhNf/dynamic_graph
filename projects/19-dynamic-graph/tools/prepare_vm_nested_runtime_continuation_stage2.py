"""Freeze runner-only routing/classification repair; do not execute a VM/C/compiler."""
import ast,difflib,hashlib,json,shutil,struct
from pathlib import Path
P=Path(__file__).resolve().parents[1];R=P/'artifacts/stage2-vm-nested-budget/runtime-integration';F=R/'continuation-supplement';OLD=R/'functional-evidence'
def sha(p):
    digest=hashlib.sha256()
    with Path(p).open('rb')as s:
        for chunk in iter(lambda:s.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    assert not F.exists();initial=read(R/'implementation-freeze/manifest.json');old=read(OLD/'report.json');audit=P.parents[1]/'outputs/stage2-root-vm-nested-runtime-first-failure.json';assert read(audit)['passed']
    assert sha(OLD/'report.json')=='35047176376fd9cb1b85b89f79883920e183a6c6a4c8cbe67fb603ea0acabdc7'
    source=P/'tools/run_vm_nested_runtime_stage2.py';text=source.read_text(encoding='utf-8');assert sha(source)==initial['runner_sha256'];before=text
    def change(a,b):
        nonlocal text
        assert text.count(a)==1,a[:70];text=text.replace(a,b)
    change("choices=['build','contracts','ctest','functional','ubsan']","choices=['functional']")
    change("assert sha(Path(__file__))==frozen['runner_sha256']", "continuation=read(R/'continuation-supplement/manifest.json');assert sha(Path(__file__))==continuation['runner_sha256'];assert sha(R/'functional-evidence/report.json')==continuation['failed_report_sha256']")
    change("out=R/(args.phase+'-evidence')", "out=R/'functional-evidence-continuation'")
    change("started=time.perf_counter()", "report['continuation_manifest_sha256']=sha(R/'continuation-supplement/manifest.json');report['initial_failed_report_sha256']=continuation['failed_report_sha256'];report['initial_raw_directory']=str(R/'functional-evidence');report['reused_runs']=[]\n    started=time.perf_counter()")
    change("old=read(P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json');initial=read(R/'initial-plan/plan.json');assert old['passed']", "failed=read(R/'functional-evidence/report.json');cache={(x['source'],x['family'],x['mode'],x['scope']):x for x in failed['functional']};assert len(cache)==586;used_cache=set();cached_fresh={s['label']:s for s in failed['sources']if 'actual_folder'in s}\n        old=read(P/'artifacts/stage2-vm-proved-budget/runtime-integration/correctness/report.json');initial=read(R/'initial-plan/plan.json');assert old['passed']")
    change("proc,resources=call(rawlabel,command);metric=json.loads(proc.stdout)\n                row={'source':label", "identity=(label,family,mode,scope)\n                if identity in cache:\n                    assert identity not in used_cache;used_cache.add(identity);row=dict(cache[identity]);assert all(row[k]==v for k,v in hashes.items());assert row['metadata']==str(metadata)and row['input']==str(ip)and row['reference']==str(ref)\n                    cached_process=next(x for x in failed['runs']if x['label']==rawlabel);assert cached_process['exit_code']==0;report['reused_runs'].append(dict(cached_process));metric=row\n                    row.update(reused_actual_execution=True,raw_stdout=str(R/'functional-evidence'/(rawlabel+'.stdout')),raw_stderr=str(R/'functional-evidence'/(rawlabel+'.stderr')),command=cached_process['command']);report['functional'].append(row);save()\n                else:\n                    proc,resources=call(rawlabel,command);metric=json.loads(proc.stdout)\n                    row={'source':label")
    # This row body is inside the new else branch; only indentation and provenance are new.
    change("'output':str(target),**hashes,**metric,**exact_compare(ref,target)};report['functional'].append(row);save()", "'output':str(target),**hashes,**metric,**exact_compare(ref,target), 'reused_actual_execution':False,'raw_stdout':str(out/(rawlabel+'.stdout')),'raw_stderr':str(out/(rawlabel+'.stderr')),'command':resources['command']};report['functional'].append(row);save()")
    change("if mode!='fixed-auto'and metric['selected_engine']=='vm':", "assert metric['vm_budget_mode']==flags[flags.index('--vm-budget')+1]\n                if metric['vm_budget_mode']!='fixed'and metric['selected_engine']=='vm':")
    change("if mode=='fixed-auto' or metric['selected_engine']!='vm':", "if metric['vm_budget_mode']=='fixed' or metric['selected_engine']!='vm':")
    fresh_start="            label=source['label'];folder=out/label;folder.mkdir(exist_ok=True);cp=folder/'source.c';shutil.copyfile(source['path'],cp);assert sha(cp)==source['sha256'];metadata=folder/'program.meta';analysis=analyze(cp,metadata,'C:/Program Files/LLVM/bin/clang.exe',source['function']);assert analysis['optimized']==('scalar_cholesky_column_dag'if label=='strict-cholesky-control'else'none'),(label,analysis['optimized'])"
    fresh_end="            report['sources'].append({**source,'actual_folder':str(folder),'metadata_sha256':sha(metadata),'analysis_sha256':sha(metadata.with_suffix('.analysis.json')),'harness_sha256':sha(folder/'oracle.c'),'oracle_EXE_sha256':sha(oracle),'analysis':analysis});save()"
    begin=text.index(fresh_start);end=text.index(fresh_end,begin)+len(fresh_end);old_block=text[begin:end]
    body=old_block.splitlines();indented='\n'.join('    '+line for line in body[1:])
    # Keep the original analysis/harness/compiler code unchanged for the two new sources only.
    new_head="""            label=source['label']
            if label in cached_fresh:
                cached_source=cached_fresh[label];folder=Path(cached_source['actual_folder']);cp=folder/'source.c';metadata=folder/'program.meta';oracle=folder/'oracle.exe';analysis=cached_source['analysis'];assert sha(cp)==source['sha256']and sha(metadata)==cached_source['metadata_sha256']and sha(oracle)==cached_source['oracle_EXE_sha256']
                report['sources'].append(dict(cached_source));save()
            else:
"""+'    '+fresh_start+ '\n'+indented
    text=text[:begin]+new_head+text[end:]
    change("                ip=folder/(family+'-input.bin');ref=folder/(family+'-oracle.bin');make_input(ip,source['sizes'],diagonal=diagonal,signed_zero=signed);call(label+'-'+family+'-trueC',[oracle,ip,ref,'32'])", """                prior_ip=folder/(family+'-input.bin');prior_ref=folder/(family+'-oracle.bin')
                if label in cached_fresh and prior_ip.exists()and prior_ref.exists():ip,ref=prior_ip,prior_ref
                else:
                    target_folder=out/label;target_folder.mkdir(exist_ok=True);ip=target_folder/(family+'-input.bin');ref=target_folder/(family+'-oracle.bin');make_input(ip,source['sizes'],diagonal=diagonal,signed_zero=signed);call(label+'-'+family+'-trueC',[oracle,ip,ref,'32'])""")
    change("report['errors'].append({'source':failure['source'],'mode':mode,'stderr':proc.stderr,'stdout':proc.stdout,'exit_code':proc.returncode})", "report['errors'].append({'source':failure['source'],'mode':mode,'stderr':proc.stderr,'stdout':proc.stdout,'exit_code':proc.returncode,'metadata':failure['metadata'],'metadata_sha256':sha(failure['metadata']),'input':str(failure_input),'input_sha256':sha(failure_input),'target':str(target),'raw_stdout':str(out/('error-'+failure['source']+'-'+mode+'.stdout')),'raw_stderr':str(out/('error-'+failure['source']+'-'+mode+'.stderr'))})")
    change("report['cli'].append({'build':label,**entry,'actual_exe':str(binary[label])})", "report['cli'].append({'build':label,**entry,'actual_exe':str(binary[label]),'raw_stdout':str(out/('CLI-'+str(index)+'.stdout')),'raw_stderr':str(out/('CLI-'+str(index)+'.stderr'))})")
    change("report['cli'].append({'build':'proved-only-compat','flags':['--help'],'stdout':proc.stdout,'stderr':proc.stderr})", "report['cli'].append({'build':'proved-only-compat','flags':['--help'],'stdout':proc.stdout,'stderr':proc.stderr,'raw_stdout':str(out/'CLI-proved-only-help.stdout'),'raw_stderr':str(out/'CLI-proved-only-help.stderr')})")
    change("assert len(report['functional'])==624", "assert used_cache==set(cache)and len(report['reused_runs'])==586\n        assert len({(x['source'],x['family'],x['mode'],x['scope'])for x in report['functional']})==624\n        assert len([x for x in report['functional']if not x['reused_actual_execution']])==38\n        assert len(report['functional'])==624")
    # Recheck sealed binary hashes rather than silently selecting a rebuilt candidate.
    change("binary={b['label']:R/b['build']/'cholesky_runtime.exe'for b in builds};report['binary_sha256']={k:sha(v)for k,v in binary.items()}", "binary={b['label']:R/b['build']/'cholesky_runtime.exe'for b in builds};report['binary_sha256']={k:sha(v)for k,v in binary.items()};assert report['binary_sha256']==continuation['runtime_sha256']")
    ast.parse(text)
    identities=[(x['source'],x['family'],x['mode'],x['scope'])for x in old['functional']];assert len(identities)==len(set(identities))==586
    file_hashes={};cached_rows=[]
    def check(path,expected):
        path=Path(path);key=str(path)
        if key not in file_hashes:file_hashes[key]=sha(path)
        assert file_hashes[key]==expected,(path,expected,file_hashes[key])
    for row in old['functional']:
        for k,f in [('metadata','metadata_sha256'),('input','input_sha256'),('reference','reference_sha256'),('output','sha256')]:check(row[k],row[f])
        process=next(x for x in old['runs']if x['label']==row['source']+'-'+row['family']+'-'+row['mode']);assert process['exit_code']==0
        for suffix in ['stdout','stderr']:check(OLD/(process['label']+'.'+suffix),process[suffix+'_sha256'])
        metric=read(OLD/(process['label']+'.stdout'));assert metric['vm_budget_mode']==process['command'][process['command'].index('--vm-budget')+1]
        cached_rows.append({'identity':list((row['source'],row['family'],row['mode'],row['scope'])),'output':row['output'],'output_sha256':row['sha256'],'reference':row['reference'],'reference_sha256':row['reference_sha256'],'raw_stdout':str(OLD/(process['label']+'.stdout')),'raw_stderr':str(OLD/(process['label']+'.stderr')),'process_label':process['label'],'runtime_exit_code':0})
    for source_row in old['sources']:
        folder=Path(source_row.get('actual_folder',source_row.get('folder','')))
        for name,key in [('source.c','sha256'if'actual_folder'in source_row else'source_sha256'),('program.meta','metadata_sha256'),('oracle.c','harness_sha256'),('oracle.exe','oracle_EXE_sha256'if'actual_folder'in source_row else'oracle_binary_sha256')]:check(folder/name,source_row[key])
    new=P/'tools/run_vm_nested_runtime_continuation_stage2.py';assert not new.exists();new.write_text(text,encoding='utf-8');F.mkdir();(F/'runner-source/tools').mkdir(parents=True)
    for path in [new,source,Path(__file__)]:shutil.copyfile(path,F/'runner-source/tools'/path.name)
    diff=''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='initial/run_vm_nested_runtime_stage2.py',tofile='continuation/run_vm_nested_runtime_continuation_stage2.py'));(F/'runner.diff').write_text(diff,encoding='utf-8')
    build=read(R/'build-evidence/report.json');binaries={k:v['artifacts']['cholesky_runtime.exe']['sha256']for k,v in build['build_inventory'].items()}
    for b in initial['builds']:check(R/b['build']/'cholesky_runtime.exe',binaries[b['label']])
    manifest={'schema':'optional-nested-VM-runtime-runner-continuation-supplement-v1','initial_implementation_manifest_sha256':sha(R/'implementation-freeze/manifest.json'),'failed_report_sha256':sha(OLD/'report.json'),'first_failure_diagnosis_sha256':sha(R/'functional-first-failure/diagnosis.json'),'root_first_failure_audit_sha256':sha(audit),'initial_runner_sha256':sha(source),'runner_sha256':sha(new),'runner_diff_sha256':sha(F/'runner.diff'),'producer_sha256':sha(Path(__file__)),'runtime_sha256':binaries,'cached_source_input_meta_reference_output_raw_actual_sha256':file_hashes,'reuse_rows':cached_rows,'reused_whole_C':586,'pending_whole_C':38,'final_unique_whole_C':624,'pending_errors':56,'pending_CLI':10,'new_source_oracle_compiles':['unknown-data-step','unknown-parent-bound-write'],'new_actual_C_reference_executions':5,'new_actual_C_reference_scope':'strict Cholesky signedzero not yet generated, plus two unknown sources x two families; already-generated oracles/inputs/Metadata/outputs/raw readonly','two_classification_fixes':'actual emitted metric vm_budget_mode, checked against actual flags budget value; no mode-name inference','future_command':[str(P/'.venv/Scripts/python.exe'),str(new),'--phase','functional'],'new_evidence_directory':str(R/'functional-evidence-continuation'),'all_624_have_raw_stdout_and_raw_stderr_paths':True,'primary_vs_compat_denominators':{'primary_whole_C':557,'compat_whole_C':67,'primary_errors':49,'compat_errors':7,'primary_CLI':9,'compat_CLI':1},'mirror_Runtime_C_Metadata_flags_or_gold_modified':False,'already_completed_C_executions_repeated':False,'new_execution_started':False}
    (F/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'prepared':True,'manifest_sha256':sha(F/'manifest.json'),'runner_sha256':sha(new),'reused':586,'pending':38,'new_VM_C_or_compiler_started':False}))
if __name__=='__main__':main()
