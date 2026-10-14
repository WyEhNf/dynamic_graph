"""Retain producer for the standalone phase3 paired runner; never run performance."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]
s=(p/'tools/benchmark_prepared_vm_tos2.py').read_text()
s=s.replace('TOS2','threaded dispatch').replace('tos2','threaded').replace('stage2-prepared-vm-phase2','stage2-prepared-vm-phase3')
s=s.replace("proof['phase1_sha256']","proof['backends']['phase1-decoded']['sha256']")
s=s.replace("'records':120","'records':130").replace('all twelve sources','all thirteen sources')
s=s.replace("'phase':'threaded dispatch stack only versus phase1 decoded algorithm in the same new EXE; no goto/fusion/plan cache'","'phase':'GNU-label dispatch versus original decoded switch in the same e27candidate/vector stack; no TOS2/fusion/plan cache; compiler-generated popinline/tailmerge/codefootprint confounding disclosed'")
s=s.replace("['https://www.lua.org/doc/sblp2005.pdf','https://www.lua.org/source/5.4/lvm.c.html','https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14']","['https://gcc.gnu.org/onlinedocs/gcc/Labels-as-Values.html','https://www.lua.org/source/5.4/ljumptab.h.html','https://jilp.org/vol5/v5paper12.pdf','https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14']")
s=s.replace("        repeat_original_matrix_stream(old/'dense-input.bin',folder/'input.bin',repeats)\n        repeat_original_matrix_stream(old/'dense-oracle.bin',folder/'oracle.bin',repeats)\n        sizes=[3,11,67,139,193,257]if source['fresh']else[3,7,17,31,33,63,64,65,127,129]", """        dense=next(r for r in proof['runs']if r['source']==label and r['family']=='dense' and r['backend']=='decoded')
        original_input=Path(dense['input']);original_output=Path(dense['reference'])
        assert sha(original_input)==dense['input_sha256']and sha(original_output)==dense['reference_sha256']
        repeat_original_matrix_stream(original_input,folder/'input.bin',repeats)
        repeat_original_matrix_stream(original_output,folder/'oracle.bin',repeats)
        sizes=[]
        with original_input.open('rb')as stream:
            count=struct.unpack('<I',stream.read(4))[0]
            for _ in range(count):
                n=struct.unpack('<I',stream.read(4))[0];sizes.append(n);stream.seek(8*n*n,1)
            assert stream.read()==b''""")
s=s.replace("'fresh_holdout':source['fresh']","'fresh_source':source['fresh_source'],'fresh_shape':source['fresh_shape'],'old_performance_source':label!='fresh-carry-fma-plain'")
s=s.replace("sha(old/'dense-oracle.bin')","sha(original_output)").replace("sha(old/'dense-input.bin')","sha(original_input)")
s=s.replace('threaded dispatch versus unchanged decoded operands','GNU-label dispatch versus unchanged decoded operands')
(p/'tools/benchmark_threaded_vm_stage3.py').write_text(s,encoding='utf-8')
