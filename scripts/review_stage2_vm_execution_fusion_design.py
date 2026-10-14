"""Independent PROGRAM CFG/entry census plus maximum-triangle evidence freeze."""
import json,time
from collections import Counter
from pathlib import Path
from review_stage2_vm_nested_next_sources import ROOT,D,read,sha
def freeze(folder,m):
    for name,row in m['frozen_files'].items():
        assert sha(folder/name)==row['sha256']==sha(row['origin']),name
        assert (folder/name).stat().st_size==row['bytes']
def main():
    maximum=D/'triangular-maximum-acceptance'; mf=read(maximum/'manifest.json')
    assert sha(maximum/'manifest.json')=='8224a4058ce7b1ba19d89b8f31c50c34f8fa8317598f9c50d81610996f4147ab'
    freeze(maximum,mf)
    actual=read(ROOT/'outputs/stage2-root-vm-nested-triangular-maximum-actual.json')
    assert actual['passed'] and actual['report_sha256']==mf['report_sha256']
    for row in mf['large_output_index']:
        assert Path(row['path']).stat().st_size==row['bytes']==actual['independently_compared_bytes']
        assert row['sha256']==actual['full_output_sha256']
    folder=D/'execution-static-design-v2'; m=read(folder/'plan.json'); freeze(folder,m)
    assert sha(folder/'plan.json')=='945a8c810bcd7e8db6c59ebe43dd159e811b16298d47ebe722cb87bad028a26f'
    assert len(m['sources'])==19 and Counter(r['actual_default_scope'] for r in m['sources'])=={'vm':18,'native':1}
    total=Counter(); sites=0
    for row in m['sources']:
        code=[line.split() for line in (folder/'programs'/row['source']/'program.meta').read_text().split('\nPROGRAM\n')[1].splitlines() if line.strip()]
        assert code==row['complete_PROGRAM']; n=len(code); targets=set(); edges={}; entries={0}
        for i,inst in enumerate(code):
            out=set(); op=inst[0]
            if op in ('JUMP','JZ','JNZ'):
                v=float(inst[1]); assert v.is_integer() and 0<=v<n
                targets.add(int(v)); out.add(int(v))
            if op not in ('JUMP','RETURN') and i+1<n:out.add(i+1)
            if op in ('JUMP','JZ','JNZ','RETURN') and i+1<n:entries.add(i+1)
            edges[i]=sorted(out)
        entries|=targets; seen=set(); todo=[0]
        while todo:
            i=todo.pop()
            if i not in seen:seen.add(i);todo.extend(edges[i])
        assert row['CFG_successors']=={str(k):v for k,v in edges.items()}
        assert row['basic_block_entries']==sorted(entries) and row['explicit_jump_targets']==sorted(targets)
        assert row['reachable_instructions']==len(seen)
        eligible={i for i in range(n-1) if i in seen and code[i][0] not in ('JUMP','JZ','JNZ','RETURN') and i+1 not in entries}
        assert eligible=={r['start_pc'] for r in row['safe_bigrams']}
        counts=Counter(code[i][0]+' '+code[i+1][0] for i in eligible)
        assert dict(counts)==row['safe_bigram_counts']; total.update(counts)
        pairs={i for i in eligible if code[i][0]==code[i+1][0]=='LOAD'}
        assert pairs=={r['start_pc'] for r in row['proposed_LOAD_LOAD_sites']};sites+=len(pairs)
    assert dict(total)==m['aggregate_static_safe_bigrams'] and sites==m['LOAD_LOAD_static_sites']==175
    assert sha(m['counterexamples_path'])==m['counterexamples_sha256']
    gold=read(m['counterexamples_path']);assert len(gold)==15 and len({r['label'] for r in gold})==15
    assert not m['default_or_Runtime_or_Metadata_changes'] and m['new_C_VM_or_compiler_executions']==0
    result=dict(passed=True,reviewed_unix=time.time(),max_triangle_freeze_sha256=sha(maximum/'manifest.json'),
        max_triangle_frozen_files=len(mf['frozen_files']),design_sha256=sha(folder/'plan.json'),source_count=19,static_LOAD_LOAD_sites=sites,
        scope='Independent full19 PROGRAM CFG/reachability/entry/safe-pair recount and219-file maximum actual acceptance freeze. Static175sites are not measured dynamic hotness or speed.',
        authorization='Isolated source-only opt-in LOAD+LOAD implementation, preserving all original PC/step/error/stack checks and perexecution discovery insidecompute. No compilation/runtime/performance/default change until source and test-driver review.')
    (ROOT/'outputs/stage2-root-vm-execution-fusion-design.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
