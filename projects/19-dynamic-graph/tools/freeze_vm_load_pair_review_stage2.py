"""Freeze static review/commands only; never invoke compiler, C or VM."""
import hashlib,json,shutil
from pathlib import Path

R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    target=R/'review-supplement';assert not target.exists();target.mkdir()
    manifest=json.loads((R/'manifest.json').read_text())
    for relative,item in manifest['frozen_files'].items():assert digest(R/relative)==item['sha256'],relative
    assert manifest['old_threaded_TU_byte_identical']
    flags=manifest['future_configure_flags']
    cmake='C:/Program Files (x86)/CMake/bin/cmake.exe'
    commands={}
    for label,extra in [('gnu',[]),('portable',['-DCHOL_THREADED_VM_FORCE_PORTABLE=ON']),('disabled',[])]:
        build_flags=[x.replace('-DCHOL_LOAD_PAIR_VM=ON','-DCHOL_LOAD_PAIR_VM=OFF')if label=='disabled'else x for x in flags]
        commands[label]={'configure':[cmake,'-S',str(R/'workspace'),'-B',str(R/('build-'+label)),'-G','MinGW Makefiles',
                                        '-DCMAKE_CXX_COMPILER=E:/mingw64/bin/g++.exe','-DCMAKE_C_COMPILER=E:/mingw64/bin/gcc.exe',*build_flags,*extra],
                         'build':[cmake,'--build',str(R/('build-'+label)),'--parallel','2'],
                         'not_executed':True}
    review={'schema':'LOAD-LOAD-static-source-review-v1','source_manifest_sha256':digest(R/'manifest.json'),
            'implemented_but_not_compiled_or_executed':True,'ordinary_and_memory_unchanged':True,
            'changed_source_sha256':{x:digest(R/'workspace'/x)for x in manifest['changed_files']},
            'contract_denominators':{'original_threaded_groups':934,'fusion_original_full_groups':15,
                                     'fusion_original_prefix_cases':8369,'numeric_bit_gold_full_cases':5,
                                     'numeric_prefix_cases':68,'chain_unusedCFG_invalidenum_extra':7,
                                     'extra_cases_total':80,'fusion_comparisons_total':8464,
                                     'each_comparison_backends':3,'all_counts_static_not_runtime_results':True},
            'bit_observation_limit':'Each returned Matrix bit and every decoded argument bit is compared. NaN payload LOAD then POP has no externally returned payload; no internal tracing claim. Explicit FMA versus mul+add independent bit gold remains distinct.',
            'full_CFG_gate':'Every enum and each JUMP/JZ/JNZ target checked without throwing. Empty/invalid complete CFG selects unfused execution; unreachable bad LOAD slot stays delayed. Full enum33 and invalid0/1/2-pop errors inherited.',
            'step_boundary':'First LOAD push, original 4096 check, second lastpc and ++steps/limit, second immediate/init/push, original NEXT4096. No span precharge or source/hash/shape routing.',
            'memory_accounting':'vm_plan_bytes includes decoded and retained byte starts. Temporary entry bitmap adds PROGRAM length bytes during discovery; allocator/header overhead not included in this logical metric. Future process PeakWS will capture it.',
            'metrics_ABI':'Every core and all linked callers must be rebuilt together from workspace/runtime.hpp. baseline-build is provenance only, never linked to new header.',
            'GNU_labels':'New TU has independent noinline/noclone owner and 33 static function-local label targets. Old threaded TU byte-identical. Compiler tail merging/actual dispatch reduction unknown until future machine-code inspection.',
            'timing':'Per-execution decode and complete CFG/disjoint discovery inside vm_prepare_ms and enclosing compute. vm_fusion_plan_ms subset; no reuse/cache. Executed pair counter counts both pushes; a second overflow may therefore count a pair before NEXT raises.',
            'future_commands':commands,'child_environment':{x:str(R/'compiler-temp')for x in ['TEMP','TMP','TMPDIR']},
            'future_resource_gates':{'fresh_RAM_before_each_build_bytes':536870912,'fresh_G_before_builds_bytes':536870912,
                                     'owned_path':str(R),'no_old_F_cleanup':True,'no_current_build_authorization':True},
            'later_fullC_and_performance':'Requires parent review/authorization and frozen actual C identities and complete byte oracle; no maximum or performance batch authorized now.',
            'G_free_bytes':shutil.disk_usage(R).free}
    (target/'review.json').write_text(json.dumps(review,indent=2)+'\n')
    shutil.copyfile(Path(__file__),target/'producer.py')
    frozen={p.relative_to(target).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size}for p in target.iterdir()if p.is_file()}
    (target/'manifest.json').write_text(json.dumps({'schema':'static-review-supplement-freeze-v1','files':frozen},indent=2)+'\n')
    print(json.dumps({'review_sha256':digest(target/'review.json'),'supplement_manifest_sha256':digest(target/'manifest.json'),
                      'source_manifest_sha256':digest(R/'manifest.json'),'no_compile_or_VM':True}))
if __name__=='__main__':main()
