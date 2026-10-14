"""Static PROGRAM CFG census and one prospective dispatch mechanism; no execution."""
import collections,json,shutil
from pathlib import Path
from benchmark_vm_nested_policy_stage2 import read,sha,write

P=Path(__file__).resolve().parents[1];STAGE=P/'artifacts/stage2-vm-nested-budget'
ROOT=STAGE/'execution-static-design-v2'
OPCODES=set('CONST LOAD STORE UNINIT READ WRITE DUP POP ADD SUB MUL DIV IDIV MOD NEG NOT BOOL TRUNC SQRT ABS MIN MAX FMA LT LE GT GE EQ NE JUMP JZ JNZ RETURN'.split())
CONTROL={'JUMP','JZ','JNZ','RETURN'}

def program(path):
    text=Path(path).read_text(encoding='utf-8');assert text.startswith('DYNCHOL 2\n')
    assert text.count('\nPROGRAM\n')==1
    rows=[line.split()for line in text.split('\nPROGRAM\n')[1].splitlines()if line.strip()]
    assert all(row[0]in OPCODES for row in rows)
    return rows

def census(rows):
    count=len(rows);edges={};targets=set();reachable=set()
    for pc,row in enumerate(rows):
        op=row[0];successors=[]
        if op in ['JUMP','JZ','JNZ']:
            assert len(row)==2;number=float(row[1]);assert number.is_integer()
            target=int(number);assert 0<=target<count
            successors.append(target);targets.add(target)
        if op not in ['JUMP','RETURN']and pc+1<count:successors.append(pc+1)
        edges[pc]=sorted(set(successors))
    pending=[0]
    while pending:
        pc=pending.pop()
        if pc in reachable:continue
        reachable.add(pc);pending.extend(edges[pc])
    entries={0}|targets|{pc+1 for pc,row in enumerate(rows)if row[0]in CONTROL and pc+1<count}
    safe=[];excluded=[];blocks=[]
    for pc in range(count-1):
        if pc not in reachable or rows[pc][0]in CONTROL:continue
        pair=rows[pc][0]+' '+rows[pc+1][0]
        target={'start_pc':pc,'second_pc':pc+1,'pair':pair,'original_instructions':rows[pc:pc+2]}
        (excluded if pc+1 in entries else safe).append(target)
    pc=0
    while pc<count:
        end=pc+1
        while end<count and end not in entries and rows[end-1][0]not in CONTROL:end+=1
        blocks.append({'start_pc':pc,'end_exclusive':end,'instructions':end-pc,'reachable':pc in reachable,
                       'ops':[r[0]for r in rows[pc:end]]})
        pc=end
    return {'instructions':count,'reachable_instructions':len(reachable),'explicit_jump_targets':sorted(targets),
            'basic_block_entries':sorted(entries),'CFG_successors':edges,'straightline_blocks':blocks,
            'safe_bigram_counts':dict(sorted(collections.Counter(r['pair']for r in safe).items())),
            'safe_bigrams':safe,'side_entry_excluded_bigrams':excluded,
            'proposed_LOAD_LOAD_sites':[r for r in safe if r['pair']=='LOAD LOAD'],
            'all_counts_static_not_executed_frequency':True}

def counterexamples():
    init=[['CONST',1.0],['STORE',1],['CONST',2.0],['STORE',2]]
    tail=[['POP'],['POP'],['CONST',0.0],['RETURN']]
    result=[]
    def add(label,code,contract,limits=None,argument_bits=None):
        result.append({'label':label,'Metadata_fields':{'algorithm':'ast_vm_v2','arithmetic':'fp64_source_order_no_implicit_fma',
                       'dependencies':'source_control_flow','optimized':'none','slots':3,'shape_slot':0,'block_slot':-1},
                       'complete_original_PROGRAM':code,'shape':3,'limits':limits or [1000000000],
                       'expected_contract':contract,'argument_bit_overrides':argument_bits or {},
                       'expected_contract_is_static_not_a_new_executed_result':True})
    add('all-prefix-budget-boundaries',init+[['LOAD',1],['LOAD',2]]+tail,
        'Budget check remains before every original opcode; report old lastpc and steps at each prefix, including rejection at either LOAD. No span-wide pre-charge.',list(range(1,11)))
    add('second-invalid-slot',init+[['LOAD',1],['LOAD',99]]+tail,'First LOAD push/overflow check precedes second step and invalid slot; second operand failure is not preparation-time.',[4,5,6,1000000000])
    add('first-invalid-slot',init+[['LOAD',99],['LOAD',2]]+tail,'First invalid slot prevents second step or slot check.',[4,5,6,1000000000])
    add('second-uninitialized',[['CONST',1.0],['STORE',1],['LOAD',1],['LOAD',2]]+tail,
        'First LOAD completes; second LOAD checks initialized scalar in the original order.',[2,3,4,1000000000])
    add('first-uninitialized',[['LOAD',1],['LOAD',2]]+tail,'First uninitialized read wins before second opcode.',[1,2,1000000000])
    add('side-entry-second',init+[['JUMP',6],['LOAD',1],['LOAD',2],['POP'],['CONST',0.0],['RETURN']],
        'Jump target6 is the second LOAD of lexical pair5..6; pair must not be fused as an inseparable entry. Original target/PC remain valid.')
    add('bad-unused-pair',init+[['CONST',0.0],['JZ',9],['LOAD',1],['LOAD',99],['POP'],['CONST',0.0],['RETURN']],
        'Unreachable invalid LOAD99 is not diagnosed during plan/fusion discovery.')
    add('overflow-after-first',init+[['CONST',0.0]]*4096+[['LOAD',1],['LOAD',2]]+tail,
        'First LOAD grows4096 to4097; stack overflow occurs before second step. A later POP must not hide the original peak.')
    add('overflow-after-second',init+[['CONST',0.0]]*4095+[['LOAD',1],['LOAD',2]]+tail,
        'First LOAD grows4095 to4096; second grows4097; exact intermediate peak/error and PC retained.')
    add('intdiv-min-overflow',[['CONST',-2147483648.0],['STORE',1],['CONST',-1.0],['STORE',2],['LOAD',1],['LOAD',2],['IDIV'],['POP'],['CONST',0.0],['RETURN']],
        'Original INTDIV pops right then left and rejects minint/-1; LOAD fusion must not bypass/reorder the arithmetic error.')
    add('integer-zero-divisor',[['CONST',1.0],['STORE',1],['CONST',0.0],['STORE',2],['LOAD',1],['LOAD',2],['MOD'],['POP'],['CONST',0.0],['RETURN']],
        'Original MOD checks denominator and signed-zero normalization; no arithmetic rewrite.')
    add('bad-read-index',init+[['LOAD',1],['LOAD',2],['ADD'],['CONST',100.0],['READ',0]]+tail,
        'Original array index/truncation/bounds checks still execute in old opcode order.')
    add('negativezero-and-subnormal',init+[['CONST',0.0],['LOAD',1],['LOAD',2],['SUB'],['WRITE',0],['CONST',0.0],['RETURN']],
        'Use direct Metadata bit overrides; LOAD preserves exact bits. Plain mul/sub and explicit fma remain distinct; no reassociation.',
        argument_bits={'0':'8000000000000000','2':'0000000000000001'})
    add('NaN-payload-slot-loads',init+[['LOAD',1],['LOAD',2],['POP'],['POP'],['CONST',0.0],['RETURN']],
        'Direct Metadata injection preserves NaN payload and signedzero through slots/LOAD; wire-format acceptance is a separate existing reader contract.',
        argument_bits={'0':'7ff8000000001234','2':'8000000000000000'})
    add('empty-return-stack',init+[['LOAD',1],['LOAD',2],['POP'],['POP'],['RETURN']],
        'Return still throws the original stack-underflow error at its original step and PC.')
    return result

def main():
    assert not ROOT.exists();ROOT.mkdir();cost=read(STAGE/'policy-cost/run-plan.json')
    cases=[c for c in cost['cases']if c['scope']=='historical13 unchanged VM streams']
    cases += [c for c in cost['cases']if c.get('family')=='dense']
    assert len(cases)==19
    records=[];frozen={}
    def copy(source,relative,digest=None):
        source=Path(source);assert digest is None or sha(source)==digest
        destination=ROOT/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        frozen[relative]={'origin':str(source),'sha256':sha(source),'bytes':source.stat().st_size}
    for case in cases:
        for name in ['source.c','program.meta']:copy(case['paths'][name],'programs/'+case['source']+'/'+name,case['hashes'][name])
        rows=program(case['paths']['program.meta'])
        records.append({'source':case['source'],'source_label':case.get('source_label',case['source']),
                        'actual_default_scope':case['kind'],'metadata_sha256':case['hashes']['program.meta'],
                        'source_sha256':case['hashes']['source.c'],'complete_PROGRAM':rows,**census(rows)})
    cases_gold=counterexamples();write(ROOT/'original-counterexamples.json',cases_gold)
    pairs=collections.Counter()
    for row in records:pairs.update(row['safe_bigram_counts'])
    copy(Path(__file__),'source/tools/'+Path(__file__).name)
    threaded=STAGE/'runtime-integration/acceptance/source/src/threaded_vm.cpp'
    copy(threaded,'source-before/src/threaded_vm.cpp')
    copy(STAGE/'policy-cost/report.json','baseline-cost/report.json')
    plan={'schema':'VM-entry-safe-static-execution-optimization-design-v1',
          'preparation_lineage':{'first_static_producer_failed':str(STAGE/'execution-static-design/first-static-failure.json'),
                                 'reason':'canonical opcode IDIV spelling repaired; first partial files/source preserved; no runtime or oracle change'},
          'status':'static design only; no implementation/compiler/VM/C/new test/performance authorization',
          'sources':records,'source_count':19,'VM_default_sources':18,'native_bypass_sources':1,
          'aggregate_static_safe_bigrams':dict(pairs.most_common()),
          'LOAD_LOAD_static_sites':sum(len(r['proposed_LOAD_LOAD_sites'])for r in records),
          'LOAD_LOAD_covered_sources':sum(bool(r['proposed_LOAD_LOAD_sites'])for r in records),
          'counterexamples_path':str(ROOT/'original-counterexamples.json'),'counterexamples_sha256':sha(ROOT/'original-counterexamples.json'),
          'counterexample_full_original_PROGRAM_count':len(cases_gold),'no_counterexample_executed':True,
          'one_prospective_mechanism':'entry-safe fixed-span LOAD+LOAD static superinstruction; no stack-cache rewrite or FP operator fusion',
          'selection':'generic adjacent opcode sequence and complete CFG entry analysis; no source/hash/N/name/data routing; unknown CFG or invalid pair falls back to original op handlers without early errors',
          'semantic_contract':['preserve a separate original step increment/limit check and lastpc before each LOAD',
                               'complete first LOAD immediate/initialized/push/NEXT overflow before considering second',
                               'keep every jump/return originalPC and all interior entries; do not fuse across an external entry',
                               'retain vector push/pop and4096 peak; no TOS2 or new FP arithmetic',
                               'keep bad unused operands dormant; decode remains perexecution insidecompute',
                               'unchanged FP64 flags and arithmetic, intUB/divzero/index/bounds/NaN/signedzero/subnormal/FMA behavior in all other handlers'],
          'goal':'eliminate one generic dispatch/enum/table lookup and repeated dependent instruction fetch between each executed eligible pair; original steps are not reduced',
          'not_proven':'Static sites do not measure executed frequency or establish branch/IP bottleneck. Original per-op safeguards may remove most gain; code growth/tail merge may lose.',
          'future_machine_code_required':'actual candidate assembly showing fewer executed dispatches/fetch dependency for eligible pair, actual tail merge/code size; no inferred speed from C++ syntax',
          'future_validation_if_authorized':'original934/33op contracts and full frozen624C/56errors, plus full prefix-step/side-entry/intermediatepeak counterexamples; meaningful gate before paired performance, no promotion merely for tests',
          'future_performance_if_authorized':'same candidate binary original threaded versus explicit fused option, fixed budget both; retain original13 streams/repeats and six unamplified freshC streams, native AUTO remains native; alternating5pairs percase, fullCbytes/computeincludingdecode/proofOFF/resources/negative; separately approved window',
          'alternatives_deferred':{'IP_loop_target_update':'2024 IP-dependency approach credible, but requires preserving checked original pc/lastpc for every jump/error; avoid combining with pair fusion in first candidate',
                                   'ORC_JIT':'larger compiler/backend/dependency/security/strictFP transition; not first bounded experiment'},
          'baseline_VM_negative_pairs':63,'default_or_Runtime_or_Metadata_changes':False,
          'primary_refs':[{'title':'Ertl/Gregg2003 Implementation Issues for Superinstructions in Gforth','url':'https://www.complang.tuwien.ac.at/anton/euroforth/ef03/ertl-gregg03.pdf','relevance':'static superinstructions can reduce dispatch and stack traffic, with hardware/code-size-dependent tradeoffs; no imported speedup claim'},
                          {'title':'Ertl/Paysan2024 VM Instruction Pointer Updates','url':'https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14','relevance':'IP dependence can constrain lightweight loop-dominated interpreters; actual host bottleneck needs measurement'},
                          {'title':'GCC Labels as Values','url':'https://gcc.gnu.org/onlinedocs/gcc/Labels-as-Values.html','relevance':'labels remain function-local; stable noinline/noclone and C++ destructor lifetime restrictions'},
                          {'title':'LLVM ORCv2','url':'https://llvm.org/docs/ORCv2.html','relevance':'possible larger JIT architecture, deliberately deferred'},
                          {'title':'Clang Users Manual FP contract','url':'https://clang.llvm.org/docs/UsersManual.html','relevance':'keep explicit ffp-contract=off with fno-fast-math'}],
          'frozen_files':frozen,'new_C_VM_or_compiler_executions':0}
    write(ROOT/'plan.json',plan)
    print(json.dumps({'prepared':True,'plan_sha256':sha(ROOT/'plan.json'),'sources':19,
                      'LOAD_LOAD_sites':plan['LOAD_LOAD_static_sites'],'covered_sources':plan['LOAD_LOAD_covered_sources'],
                      'counterexamples':len(cases_gold),'compiler_C_VM_or_tests_executed':False}),flush=True)

if __name__=='__main__':main()
