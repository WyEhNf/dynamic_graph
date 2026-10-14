"""Verify the actual ordinary install using frozen C references; no new oracle."""
import argparse,hashlib,json,re,shutil,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
from evaluate_source import exact_compare,run_runtime

def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def read(x):return json.loads(Path(x).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--resume',action='store_true');args=ap.parse_args()
    p=Path(__file__).resolve().parents[1];stage=p/'artifacts/stage2-vm-default-integration';root=stage/'ordinary-install'
    if not args.resume:root.mkdir(exist_ok=False)
    else:assert root.is_dir()and not(root/'release-manifest.json').exists()
    accepted=read(stage/'acceptance-manifest.json');maximum=read(stage/'maximum-shape/report.json')
    assert accepted['passed']and maximum['passed']and maximum['status']=='complete'
    assert maximum['default_budget_passed']is False and maximum['explicit_budget_passed']is True
    exe=p/'build/cholesky_runtime.exe';flags=p/'build/CMakeFiles/cholesky_core.dir/flags.make'
    assert flags.read_bytes()==(stage/'candidate-source/build-stage2-vm-default/CMakeFiles/cholesky_core.dir/flags.make').read_bytes()
    cache=(p/'build/CMakeCache.txt').read_text()
    for x in ['CHOL_PREPARED_VM:BOOL=ON','CHOL_THREADED_VM:BOOL=ON','CHOL_THREADED_VM_FORCE_PORTABLE:BOOL=OFF','CHOL_PACKED_READY_KEYS:BOOL=OFF']:assert x in cache,x
    assert sha(p/'build-memory/cholesky_runtime.exe')==accepted['memory_installed_sha256']
    for name,digest in accepted['source_sha256'].items():
        if name.startswith(('src/','include/'))or name in ['CMakeLists.txt','CMakePresets.json']:assert sha(p/name)==digest,name
    shutil.copyfile(exe,root/'runtime.exe');runtime_sha=sha(exe)
    report=read(root/'verification-report.json')if args.resume else {'passed':False,'status':'running','actual_runtime_sha256':runtime_sha,'installed_path':str(exe),'source_acceptance_sha256':sha(stage/'acceptance-manifest.json'),'maximum_report_sha256':sha(stage/'maximum-shape/report.json'),'ordinary_core_flags_equal_accepted':True,'runs':[],'failures':[]}
    assert not report['passed']and report['actual_runtime_sha256']==runtime_sha
    began=time.perf_counter()
    def save():
        report['elapsed_seconds']=time.perf_counter()-began;(root/'verification-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    command=['ctest','--test-dir',str(p/'build'),'--output-on-failure','-j','1','-E','source_pipeline|integer_selector_pipeline']
    if args.resume:
        stdout=(root/'ctest.stdout').read_text(encoding='utf-8')
        report['producer_recovery']={'original_actual_exit_codes':[1,1],'reasons':['CTest timing contained multiple spaces','historical wire source referenced through original oracle harness, not copied into per-source folder'],'producer_snapshots':{'before_log_parser':sha(root/'producer-before-log-parser-fix.py'),'before_source_path':sha(root/'producer-before-source-path-fix.py')},'completed_CTest_and_C_outputs_reused':True,'runtime_failures':False}
    else:
        proc=subprocess.run(command,capture_output=True,text=True,check=True);stdout=proc.stdout
        (root/'ctest.stdout').write_text(stdout,encoding='utf-8');(root/'ctest.stderr').write_text(proc.stderr,encoding='utf-8')
    assert '100% tests passed, 0 tests failed out of 8'in stdout
    report['installed_ctest']={'tests':8,'actual_exit_code':0,'command':command,'stdout_sha256':sha(root/'ctest.stdout'),'stderr_sha256':sha(root/'ctest.stderr'),'seconds':float(re.search(r'Total Test time \(real\) =\s+([0-9.]+)',stdout)[1])};save()
    old=read(stage/'correctness/report.json')
    for r in old['runs']:
        if r['backend']!='new-default':continue
        done=[x for x in report['runs']if x['scope']=='generic'and x['source']==r['source']and x['family']==r['family']]
        if done:
            assert len(done)==1 and sha(Path(done[0]['output']))==done[0]['sha256'];continue
        ip=Path(r['input']);ref=Path(r['reference']);meta=Path(r['metadata'])
        assert sha(ip)==r['input_sha256']and sha(ref)==r['reference_sha256']and sha(meta)==r['metadata_sha256']
        output=root/'generic'/(r['source']+'-'+r['family']+'.bin');output.parent.mkdir(exist_ok=True)
        command=[str(exe),'--metadata',str(meta),'--input',str(ip),'--output',str(output),'--engine','auto','--threads','4']
        proc=subprocess.run(command,capture_output=True,text=True,check=True);metrics=json.loads(proc.stdout)
        assert metrics['selected_engine']=='vm'and metrics['vm_backend']=='decoded-threaded'and metrics['vm_steps']==r['vm_steps']
        report['runs'].append({'scope':'generic','source':r['source'],'family':r['family'],'metadata':str(meta),'metadata_sha256':sha(meta),'input':str(ip),'input_sha256':sha(ip),'reference':str(ref),'reference_sha256':sha(ref),'output':str(output),'command':command,'actual_exit_code':proc.returncode,**metrics,**exact_compare(ref,output)});save()
    ip=p/'artifacts/stage2-prepared-vm-phase1/correctness/failure-input.bin'
    assert sha(ip)==old['failure_input_sha256']
    for f in old['failures']:
        if any(x['source']==f['source']for x in report['failures']):continue
        meta=Path(f['metadata']);assert sha(meta)==f['metadata_sha256'];out=root/(f['source']+'-rejected.bin')
        cmd=[str(exe),'--metadata',str(meta),'--input',str(ip),'--output',str(out),'--engine','auto']
        proc=subprocess.run(cmd,capture_output=True,text=True)
        assert proc.returncode==1 and proc.stderr==f['results'][0]['stderr']and not out.exists()and not Path(str(out)+'.partial').exists()
        report['failures'].append({'source':f['source'],'command':cmd,'metadata_sha256':sha(meta),'input_sha256':sha(ip),'actual_exit_code':proc.returncode,'stderr':proc.stderr});save()
    history=p/'artifacts/stage2-runtime-release'
    for scope in ['wire','smallest']:
        evidence=read(history/scope/'report.json');assert evidence['passed']
        for source in evidence['sources']:
            label=source['label'];folder=history/scope/label
            actual_source=folder/'source.c'
            if not actual_source.exists():actual_source=Path(re.search(r'^#include "([^"]+)"',(folder/'oracle.c').read_text(),re.MULTILINE)[1])
            assert sha(actual_source)==source['source_sha256']
            formats=source['formats']if scope=='wire'else[{'schema':source['selection']['schema'],'mode':source['selection']['mode'],'sha256':source['selection']['sha256'],'runs':source['runs']}]
            for format in formats:
                meta=folder/(f"schema{format['schema']}-{format['mode']}.meta"if scope=='wire'else'minimum.meta');assert sha(meta)==format['sha256']
                for r in format['runs']:
                    done=[x for x in report['runs']if x['scope']==scope and x['source']==label and x['family']==r['family']and x['schema']==format['schema']and x['mode']==format['mode']and x['engine']==r['engine']]
                    if done:
                        assert len(done)==1 and sha(Path(done[0]['output']))==done[0]['sha256'];continue
                    ip=folder/(r['family']+'-input.bin');ref=folder/(r['family']+'-oracle.bin');assert sha(ref)==r['sha256']
                    output=root/scope/(label+'-'+r['family']+'-'+str(format['schema'])+'-'+format['mode']+'-'+r['engine']+'.bin');output.parent.mkdir(exist_ok=True)
                    metrics=run_runtime(exe,meta,ip,output,engine=r['engine'],tile_size=7,threads=1,block=7)
                    report['runs'].append({'scope':scope,'source':label,'family':r['family'],'schema':format['schema'],'mode':format['mode'],'engine':r['engine'],'metadata':str(meta),'metadata_sha256':sha(meta),'input':str(ip),'input_sha256':sha(ip),'reference':str(ref),'reference_sha256':sha(ref),'output':str(output),'actual_exit_code':0,**metrics,**exact_compare(ref,output)});save()
    counts={scope:sum(r['scope']==scope for r in report['runs'])for scope in ['generic','wire','smallest']}
    assert counts=={'generic':63,'wire':60,'smallest':24}
    assert sha(exe)==runtime_sha and sha(p/'build-memory/cholesky_runtime.exe')==accepted['memory_installed_sha256']
    report.update(passed=True,status='complete',whole_C_outputs=len(report['runs']),scope_counts=counts);save()
    # Publish current status only after the actual installed binary passed.
    readme=p/'README.md';text=readme.read_text(encoding='utf-8')
    current=(f'当前普通 Release `{runtime_sha[:12]}...` 已接入验收后的 VM 默认后端：保持 native/AUTO 优先，真正需要 VM 的程序在 GNU 构建中默认使用 `decoded-threaded`，portable 回退到 `decoded-fallback`；显式 `--vm-backend legacy|decoded|decoded-threaded` 保留。实际普通安装通过8项合同及147份原C全文件复验，隔离 GNU/portable 各12项回归、378份原C对照。N10000 while-copy三个后端在明确1e10预算下逐字节通过，默认1e9仍明确拒绝1,700,000,012步；这不是默认预算的通用N10000通过。原4f73完整回滚与memory7da06保留，native数学、Metadata完整图、AUTO块规则和严格FP不变。见[当前VM默认集成](docs/stage2-vm-default-integration.md)及`artifacts/stage2-vm-default-integration/ordinary-install/release-manifest.json`。\n\n')
    first=text.index('\n')+1;text=text[:first]+'\n'+current+text[first:]
    text=text.replace('第三阶段可选 GNU labels','第三阶段冻结研究（当时默认OFF）：可选 GNU labels')
    text=text.replace('普通已发布EXE保持冻结','普通发布仍不启用压缩容器')
    text=text.replace('普通已验收 4f73 与 memory 二进制冻结','历史已验收 4f73 与 memory 二进制冻结')
    text=text.replace('当前普通基座另通过8/8 CTest（110.40秒）和新wire/min全文件验证，发布来源单列在`artifacts/stage2-runtime-release/`。','历史4f73基座另通过8/8 CTest（110.40秒）和wire/min全文件验证，来源仍在`artifacts/stage2-runtime-release/`；当前普通发布验收见本文开头的新manifest。')
    readme.write_text(text,encoding='utf-8')
    doc=p/'docs/stage2-vm-default-integration.md';text=doc.read_text(encoding='utf-8')
    text=text.replace('# Validated VM default integration: isolated functional gates passed','# Validated VM default integration: ordinary installed and maximum shape verified')
    text=text.replace('Ordinary4f73 and memory7da06 binaries remain installed and unchanged;\nmaximum-shape testing and ordinary installation are still pending.',f'Ordinary Release `{runtime_sha}` is now installed. Its actual8 contract tests\nand147 complete C outputs (63 generic,60 wire,24 minimum-format) passed,\nplus7 exact error contracts. The isolated functional acceptance remains\nfrozen. Old4f73 is archived and memory7da06 remains installed unchanged.')
    marker='## Independent future budget policy decision'
    results=('## Actual maximum-shape result\n\nThe frozen plan completed with actual exit0. OriginalC was reexecuted and\nall three backend outputs matched its entire800,000,008 bytes, including\n1,700,000,012 original opcode steps. Every process launch passed a fresh\n2.5GiB RAM gate. GNU default1e9 rejected exactly with the original error\nand no published/partial output; only explicit1e10 configurations passed.\nActual PeakWS values were1,605,718,016/1,605,718,016/1,606,373,376 bytes\nfor GNU auto/decoded/portable auto; commit and background CPU are preserved\nin `maximum-shape/report.json`. These sequential resource tests are not a\nnew paired performance claim. The accepted source/flags, ordinary actual\nbinary, current documentation and147 installation outputs are frozen in\n`ordinary-install/`; old manifests and sources remain unchanged.\n\n')
    assert marker in text;text=text.replace(marker,results+marker);doc.write_text(text,encoding='utf-8')
    snap=root/'released-source';hashes={}
    for x in sorted((stage/'candidate-source').rglob('*')):
        if x.is_file():
            name=x.relative_to(stage/'candidate-source');out=snap/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,out);hashes[name.as_posix()]=sha(out)
    for x in [p/'README.md',p/'docs/stage2-vm-default-integration.md',Path(__file__)]:
        name=x.relative_to(p);out=snap/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(x,out);hashes[name.as_posix()]=sha(out)
    for name in ['CMakeCache.txt','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/link.txt']:
        out=root/'released-build'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p/'build'/name,out)
    manifest={'passed':True,'status':'ordinary installed and verified','released_at_utc':datetime.now(timezone.utc).isoformat(),'installed_runtime':str(exe),'runtime_sha256':runtime_sha,'frozen_runtime':str(root/'runtime.exe'),'source_sha256':hashes,'source_count':len(hashes),'verification_report_sha256':sha(root/'verification-report.json'),'isolated_acceptance_sha256':sha(stage/'acceptance-manifest.json'),'maximum_shape_report_sha256':sha(stage/'maximum-shape/report.json'),'ordinary_core_flags_equal_accepted':True,'installed_ctest':8,'isolated_GNU_portable_CTest_each':12,'installed_whole_C_outputs':147,'installed_error_contracts':7,'GNU_default':'auto -> decoded-threaded for VM-required programs; native priority unchanged','portable_default':'decoded-fallback when labels unavailable','prepared_disabled_default':'legacy','explicit_overrides_preserved':True,'default_step_limit':1000000000,'maximum_shape_default_budget_passed':False,'maximum_shape_explicit_budget_passed':True,'supported_Metadata':[1,2,3],'frontend_default_schema':2,'native_AUTO_unchanged':True,'strict_FP_flags_unchanged':True,'packed_ready_keys':'OFF','ordinary_rollback':str(stage/'rollback4f73/cholesky_runtime.exe'),'ordinary_rollback_sha256':accepted['ordinary_installed_sha256'],'memory_unchanged_sha256':accepted['memory_installed_sha256'],'no_new_performance_claim':True}
    (root/'release-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'installed_sha256':runtime_sha,'whole_C_outputs':147,'CTest':8,'manifest_sha256':sha(root/'release-manifest.json'),'default_budget':1000000000,'maximum_default_success':False},indent=2),flush=True)
if __name__=='__main__':main()
