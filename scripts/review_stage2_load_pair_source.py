"""Root source, full original counterexample serialization and ABI plan audit."""
import json,re,struct,time
from pathlib import Path
from review_stage2_vm_nested_next_sources import ROOT,P,D,read,sha
G=Path('G:/Hackathon-stage2-artifacts/project19/load-pair')
def main():
    m=read(G/'manifest.json');review=read(G/'review-supplement/review.json')
    assert sha(G/'manifest.json')=='f9c6137f228db66f778491b8ab8836ec15cde512543df32b579005318a84d700'
    for name,r in m['frozen_files'].items():assert sha(G/name)==r['sha256'] and (G/name).stat().st_size==r['bytes'],name
    supplement=read(G/'review-supplement/manifest.json')
    for name,r in supplement['files'].items():
        path=G/'review-supplement'/name
        assert sha(path)==r['sha256'] and path.stat().st_size==r['bytes']
    old=G/'source-before';new=G/'workspace';accept=D/'runtime-integration/acceptance/source';unchanged=matched=0
    for path in old.rglob('*'):
        if not path.is_file():continue
        name=path.relative_to(old)
        if (accept/name).is_file():assert sha(path)==sha(accept/name);matched+=1
        if str(name).replace('\\','/') not in m['changed_files']:assert sha(path)==sha(new/name),str(name);unchanged+=1
    assert matched==178 and sha(old/'src/threaded_vm.cpp')==sha(new/'src/threaded_vm.cpp')
    a=(old/'src/threaded_vm.cpp').read_text();b=(new/'src/load_pair_vm.cpp').read_text()
    assert a[a.index('LStore:'):]==b[b.index('LStore:'):]
    assert a[a.index('#define DISPATCH()'):a.index('LConst:')]==b[b.index('#define DISPATCH()'):b.index('LConst:')]
    assert sha(new/'include/cholesky/runtime.hpp')==m['new_header_ABI_sha256']
    assert sha(G/'original-counterexamples.json')==sha(D/'execution-static-design-v2/original-counterexamples.json')
    code=(new/'tests/load_pair_vm_tests.cpp').read_text();groups=re.findall(r'group\("([^"]+)",meta\(\{(.*?)\}\),"([^"]*)",\{(.*?)\}\);',code,re.S)
    gold=read(G/'original-counterexamples.json');assert len(groups)==len(gold)==15
    mapping={'IDIV':'IntDiv','JZ':'Jz','JNZ':'Jnz'};prefix=0
    for (label,body,error,limits),case in zip(groups,gold):
        assert label==case['label'];instructions=re.findall(r'\{O::(\w+),([^{}]+)\}',body);original=case['complete_original_PROGRAM'];assert len(instructions)==len(original)
        for i,((op,arg),row) in enumerate(zip(instructions,original)):
            assert op==mapping.get(row[0],row[0].title()),(label,i)
            bits=case['argument_bit_overrides'].get(str(i))
            if bits:assert arg==f'std::bit_cast<double>(UINT64_C(0x{bits}))'
            else:assert struct.pack('<d',float(arg))==struct.pack('<d',float(row[1]) if len(row)>1 else 0.0)
        prefix+=len(original)+2
    assert prefix==review['contract_denominators']['fusion_original_prefix_cases']==8369
    assert review['contract_denominators']['fusion_comparisons_total']==15+prefix+80==8464
    assert 'limit<=p.size()+1' in code and 'i<=m.program.size()+1' in code
    for row in review['future_commands'].values():
        assert '-DCHOL_PROVED_VM_BUDGET=OFF' in row['configure'] and '-DCHOL_NESTED_VM_BUDGET=OFF' in row['configure']
        assert row['build'][-2:]==['--parallel','2']
    assert not m['default_auto_backend_changed'] and m['no_compile_VM_C_or_small_test']
    result=dict(passed=True,reviewed_unix=time.time(),source_manifest_sha256=sha(G/'manifest.json'),frozen_files=len(m['frozen_files']),original_accepted_source_files=matched,unchanged_old_files=unchanged,new_ABI_sha256=m['new_header_ABI_sha256'],full_original_groups=15,all_prefix_cases=prefix,comparisons_per_enabled_build=8464,original_threaded_contracts=934,
        scope='441 sources/baselines and source-before178 accepted originals checked; oldthreaded unchanged, all33 other handlers/dispatch text exact. Full15 originalPROGRAM literal op/IEEE bits independently matched to preimplementation gold, zero-through-onepast prefixes preserved. Source-only review cannot prove actual correctness or dispatch speed.',
        authorization='One sequential GNU-enabled/forced-portable/disabled complete matching-ABI build batch and fullCTest, new8464+old934 contracts on enabled builds, strictFP/file-backed logs/ownedG temp and freshRAM>=1GiB/Gfree>=1GiB at launch. No performance/fullC/default promotion until actual contracts independently audited; preserve first failure and no timeout restart.')
    (ROOT/'outputs/stage2-root-load-pair-source.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
