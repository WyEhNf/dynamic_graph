"""Self-set competition-shaped tests with independent C oracles and strict bytes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import time
from datetime import datetime, timezone
from analyze_source import analyze
from evaluate_source import evaluate, make_input, compile_oracle, exact_compare, run_runtime


def reject(runtime, metadata, data, root, label, extra=()):
    source = root / f"reject-{label}.bin"; source.write_bytes(data)
    output = root / f"reject-{label}-out.bin"; output.unlink(missing_ok=True)
    partial=Path(str(output)+'.partial');partial.unlink(missing_ok=True)
    run = subprocess.run([str(runtime.resolve()),"--metadata",str(metadata.resolve()),"--input",str(source.resolve()),"--output",str(output.resolve()),*extra],capture_output=True,text=True,timeout=20)
    if run.returncode == 0 or output.exists() or partial.exists(): raise AssertionError(f"invalid case accepted or partial file leaked: {label}")
    return {"case": label, "rejected": True, "message": run.stderr.strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=Path("build/cholesky_runtime.exe"))
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--gcc", default="gcc")
    parser.add_argument("--profile", choices=("quick","full"), default="full")
    parser.add_argument("--large-shape", type=int, default=0, help="0 skips large diagonal; use 10000 to cover maximum shape, ~1.6GB live matrix memory")
    parser.add_argument("--output-dir",type=Path,default=Path("artifacts/phase1-tests"))
    args = parser.parse_args()
    runtime = args.runtime.resolve(); root = args.output_dir.resolve(); root.mkdir(parents=True,exist_ok=True)
    project = Path(__file__).resolve().parent.parent
    sizes = [3,4,7,16,17,31,32,33,65] if args.profile == "quick" else [3,4,7,16,17,31,32,33,63,64,65,67,127,128,129]
    blocked_sizes = [3,7,17,31,32,33,65]
    cases = []
    declarations = [
        ("scalar",project/"fixtures/cholesky_reference.c","cholesky_reference",sizes,(32,)),
        ("page-naive",project/"fixtures/official_naive_transcribed.c","cholesky",sizes,(32,)),
        ("blocked",project/"fixtures/cholesky_blocked.c","cholesky_blocked",blocked_sizes,(1,2,7,16,32,100)),
    ]
    source = (project/"fixtures/cholesky_reference.c").read_text(encoding="utf-8")
    names = {"cholesky_reference":"decompose","a":"input_matrix","l":"factor","n":"extent","i":"row","j":"column","k":"depth","sum":"accumulator"}
    renamed = re.sub(r"\b(" + "|".join(names) + r")\b", lambda m:names[m[0]],source)
    renamed = renamed.replace("++row","row += 1").replace("++column","column = column + 1").replace("++depth","depth++")
    rename_path=root/"renamed.c"; rename_path.write_text(renamed,encoding="utf-8")
    declarations.append(("renamed-loop-forms",rename_path,"decompose",[3,17,65],(32,)))
    # The same named function with changed arithmetic must compile to different
    # metadata and execute its changed semantics, not a fixed Cholesky kernel.
    changed=(project/"fixtures/official_naive_transcribed.c").read_text(encoding="utf-8").replace("return x * y + z;","return x * y * 0.5 + z;")
    changed_path=root/"changed-arithmetic.c"; changed_path.write_text(changed,encoding="utf-8")
    declarations.append(("changed-arithmetic",changed_path,"cholesky",[3,17,33],(32,)))
    fused=(project/"fixtures/official_naive_transcribed.c").read_text(encoding="utf-8").replace("return x * y + z;","return fma(x,y,z);")
    fused_path=root/"explicit-fma.c"; fused_path.write_text(fused,encoding="utf-8")
    declarations.append(("explicit-fma",fused_path,"cholesky",[3,17,65],(32,)))
    generic=root/"generic.c"
    generic.write_text('''int transform(const double *a,double *l,int n) {
  int i=0;
  while(i<n*n) {
    if(i<n*n && a[i]>=0.0) l[i]=a[i]/2.0;
    else l[i]=-a[i];
    i=i+1;
  }
  return 0;
}
''',encoding="utf-8")
    declarations.append(("generic-while-if",generic,"transform",[3,17,33],(32,)))
    official=(project/'fixtures/official_naive_transcribed.c').read_text(encoding='utf-8')
    variants={
      'commuted-integer-address':re.sub(r'([ijk])\*n\+([ijk])',r'\2+n*\1',official),
      'equivalent-right-loop-bounds':official.replace('i < n','i <= n-1').replace('j < n','j <= n-1').replace('k <= j','k < j+1').replace('i++','i = 1+i').replace('j++','j += 1').replace('k++','++k').replace('i+1','1+i'),
      'pure-ssa-helpers':official.replace('return x / y;','double quotient=x/y; return quotient;').replace('return x * y + z;','double product=x*y; double result=product+z; return result;'),
      'changed-ssa-arithmetic':official.replace('return x * y + z;','double product=x*y*0.5; return product+z;'),
    }
    for label,variant in variants.items():
        path=root/f'{label}.c';path.write_text(variant,encoding='utf-8');declarations.append((label,path,'cholesky',[3,7,17,33,65],(32,)))
    integer_helper=root/'ssa-integer-conversion.c';integer_helper.write_text('''static double conversion(double x){int truncated=x; double converted=truncated;return converted/2.0;}
int transform(const double*a,double*l,int n){for(int i=0;i<n*n;++i)l[i]=conversion(a[i]);return 0;}
''',encoding='utf-8');declarations.append(('ssa-integer-conversion',integer_helper,'transform',[3,17,33],(32,)))
    integer_arithmetic=root/'typed-integer-arithmetic.c';integer_arithmetic.write_text('''int transform(const double*a,double*l,int n){
for(int i=0;i<n*n;++i){
  if(i%4==0)l[i]=-i;
  else if(i%4==1)l[i]=(-i)/n;
  else if(i%4==2)l[i]=(-i)%2;
  else l[i]=(-i)*0;
}return 0;}
''',encoding='utf-8');declarations.append(('typed-integer-arithmetic',integer_arithmetic,'transform',[3,17,33],(32,)))
    for label,path,function,shape,blocks in declarations:
        case=evaluate(path,function,runtime,root/label,shape,args.clang,args.gcc,blocks,(1,2,4),True)
        if label in ("changed-arithmetic","generic-while-if","changed-ssa-arithmetic","ssa-integer-conversion","typed-integer-arithmetic") and case["optimized"] != "none": raise AssertionError("unproven arithmetic was incorrectly optimized")
        if label in variants and label!='changed-ssa-arithmetic'and case['optimized']!='rightlooking_cholesky_column_dag':raise AssertionError('valid semantic variant lost its operation graph proof')
        if label == "explicit-fma" and case["optimized"] != "rightlooking_cholesky_column_dag_fma": raise AssertionError("explicit FMA semantics lost")
        cases.append({"case":label,**case}); print(f"PASS {label}: {len(case['runs'])} strict C oracle comparisons",flush=True)
    scalar_metadata=root/"scalar/program.meta"
    page_metadata=root/"page-naive/program.meta"
    # Fast diagonal specialization is separately checked against executable C,
    # source VM and signed-zero bytes before being used for maximum-shape tests.
    diagonal_input=root/"diagonal-signed-zero.bin"; make_input(diagonal_input,[3,17,65],True,True)
    diagonal_runs=[]
    for label,path,function,_,_ in declarations[:3]:
        folder=root/label; metadata=folder/"program.meta"; oracle=folder/"oracle.exe"
        reference=folder/"diagonal-oracle.bin"
        subprocess.run([str(oracle),str(diagonal_input),str(reference),"7"],check=True)
        for engine in ("auto","vm"):
            target=folder/f"diagonal-{engine}.bin"
            metrics=run_runtime(runtime,metadata,diagonal_input,target,block=7,engine=engine)
            diagonal_runs.append({"case":label,**metrics,**exact_compare(reference,target)})
    print("PASS signed-zero diagonal: C oracle, source VM and optimized paths",flush=True)
    # Repeated parallel schedules and non-power-of-two worker counts.
    repeat_input=root/"repeat-input.bin"; make_input(repeat_input,[129])
    repeat_oracle=root/"repeat-oracle.bin"
    subprocess.run([str(root/"page-naive/oracle.exe"),str(repeat_input),str(repeat_oracle),"32"],check=True)
    repeated=[]
    for threads in (1,2,3,4):
        for index in range(3 if args.profile=="quick" else 5):
            target=root/"repeat-output.bin"; metrics=run_runtime(runtime,page_metadata,repeat_input,target,threads=threads)
            repeated.append({"repeat":index,**metrics,**exact_compare(repeat_oracle,target)})
    print(f"PASS repeated parallel: {len(repeated)} runs",flush=True)
    valid=struct.pack("<II9d",1,3,4,0,0,0,9,0,0,0,16)
    rejection=[]
    malformed={"truncated_header":b'\x01',"n_below_min":struct.pack('<II',1,2),"n_above_max":struct.pack('<II',1,10001),"truncated_payload":struct.pack('<II',1,3)+b'\0'*8,"trailing_payload":valid+b'x',"non_spd":struct.pack('<II9d',1,3,-1,0,0,0,9,0,0,0,16),"non_finite":struct.pack('<II9d',1,3,float('nan'),0,0,0,9,0,0,0,16)}
    for label,data in malformed.items(): rejection.append(reject(runtime,page_metadata,data,root,label))
    rejection.append(reject(runtime,page_metadata,valid,root,"zero-block",("--block-size","0")))
    bad_metadata=root/"invalid-jump.meta"
    bad_metadata.write_text(page_metadata.read_text(encoding="utf-8").replace("JUMP 3","JUMP 1000000"),encoding="utf-8")
    # Make the malformed jump independent of the compiler's instruction offset.
    lines=page_metadata.read_text(encoding="utf-8").splitlines(); jump=next(i for i,line in enumerate(lines) if line.startswith("JUMP ")); lines[jump]="JUMP 1000000"; bad_metadata.write_text('\n'.join(lines)+'\n',encoding="utf-8")
    rejection.append(reject(runtime,bad_metadata,valid,root,"invalid-jump"))
    rejection.append(reject(runtime,page_metadata,valid,root,"step-limit",("--engine","vm","--vm-step-limit","1")))
    # These programs invoke undefined C integer behavior. No C oracle is run:
    # the defined local contract is to detect it rather than fabricate a result.
    integer_failures={
        'int-add-overflow':'int x=2147483647;l[0]=x+n;',
        'int-multiply-overflow':'int x=50000;l[0]=x*x;',
        'int-negate-minimum':'int x=-2147483647-1;l[0]=-x;',
        'int-divide-minimum':'int x=-2147483647-1;int y=-1;l[0]=x/y;',
        'int-remainder-minimum':'int x=-2147483647-1;int y=-1;l[0]=x%y;',
        'fp-to-int-range':'int x=a[0]*1e100;l[0]=x;',
        'integer-zero-divisor':'int x=n-n;l[0]=n/x;',
    }
    for label,body in integer_failures.items():
        source=root/f'{label}.c';source.write_text('int transform(const double*a,double*l,int n){'+body+'return 0;}',encoding='utf-8')
        metadata=root/f'{label}.meta';analyze(source,metadata,args.clang,'transform')
        rejection.append(reject(runtime,metadata,valid,root,label,('--engine','vm')))
    for label,opcode,replacement in [('missing-constant-operand','CONST','CONST'),('unexpected-add-operand','ADD','ADD 1'),('extra-opcode-token','ADD','ADD 0 extra')]:
        lines=page_metadata.read_text(encoding='utf-8').splitlines()
        position=next(i for i,line in enumerate(lines)if line.split()[0]==opcode)
        lines[position]=replacement;metadata=root/f'{label}.meta';metadata.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        rejection.append(reject(runtime,metadata,valid,root,label))
    # The physical block is independent of source block. Reject an excessive
    # graph before cache allocation and remove the already-open output stream.
    cap_input=root/'graph-cap-input.bin';make_input(cap_input,[1000])
    rejection.append(reject(runtime,page_metadata,cap_input.read_bytes(),root,'physical-graph-cap',('--engine','tiled','--tile-size','1')))
    cap_input.unlink()
    unsupported=root/"unsupported.c"; unsupported.write_text('int cholesky_reference(const double*a,double*l,int n){l[0]=a[0]; a[0]=1;return 0;}',encoding="utf-8")
    try:
        analyze(unsupported,root/"unsupported.meta",args.clang,"cholesky_reference")
    except ValueError as error:
        rejection.append({"case":"immutable-input-source","rejected":True,"message":str(error)})
    else: raise AssertionError("unsupported source side effect was accepted")
    for label,helper in [('helper-side-effect','static double h(double x){x+=1;return x;}'),('helper-uninitialized','static double h(double x){double y=y;return y+x;}')]:
        source=root/f'{label}.c';source.write_text(helper+'\nint transform(const double*a,double*l,int n){l[0]=h(a[0]);return 0;}',encoding='utf-8')
        try:analyze(source,root/f'{label}.meta',args.clang,'transform')
        except ValueError as error:rejection.append({'case':label,'rejected':True,'message':str(error)})
        else:raise AssertionError('unsupported helper was accepted')
    performance=[]
    if args.profile == "full":
        for n in (256,512,1024):
            folder=root/f"performance-{n}"; folder.mkdir(exist_ok=True)
            input_path=folder/"input.bin"; make_input(input_path,[n])
            reference=folder/"oracle.bin"; subprocess.run([str(root/"page-naive/oracle.exe"),str(input_path),str(reference),"32"],check=True)
            for threads in (1,4):
                for repeat in range(3):
                    target=folder/"runtime.bin"; metrics=run_runtime(runtime,page_metadata,input_path,target,threads=threads)
                    performance.append({"n":n,"repeat":repeat,**metrics,**exact_compare(reference,target)})
            print(f"PASS dense performance n={n}: strict C oracle, 3 runs per thread count",flush=True)
    large_shape={"executed":False,"general_dense_n10000_executed":False}
    if args.large_shape:
        if not 3 <= args.large_shape <= 10000: raise ValueError("large-shape must be in [3,10000]")
        input_path=root/"large-diagonal-input.bin"; output_path=root/"large-diagonal-output.bin"; expected=root/"large-diagonal-expected.bin"
        make_input(input_path,[args.large_shape],True)
        metrics=run_runtime(runtime,page_metadata,input_path,output_path)
        # Independent analytic oracle: powers-of-four diagonal -> exact integer
        # roots, all other output entries are +0. No runtime output feeds oracle.
        with expected.open('wb') as stream:
            from array import array
            stream.write(struct.pack('<II',1,args.large_shape))
            for i in range(args.large_shape):
                row=array('d',[0.0])*args.large_shape; row[i]=float(2**(i%4)); stream.write(row.tobytes())
        large_shape={"executed":True,"n":args.large_shape,"fixture":"full dense binary layout, structured diagonal SPD; data-dependent specialization", "oracle":"independent exact analytic roots and +0 bytes", "general_dense_n10000_executed":False,**metrics,**exact_compare(expected,output_path)}
        for path in (input_path,output_path,expected): path.unlink()
        print(f"PASS maximum-format shape n={args.large_shape}: analytic strict bytes; large files removed after verification",flush=True)
    report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),"profile":args.profile,"passed":True,"comparison":"strict IEEE754 full-file bytes; no tolerance substitution","source_cases":cases,"signed_zero_diagonal":diagonal_runs,"repeated_parallel":repeated,"rejection_cases":rejection,"performance":performance,"large_shape":large_shape,"official_package_used":False,"official_page_algorithm_transcribed":True,"local_contract":{"io":"little-endian uint32 M,N; row-major FP64; same output layout","output_initialization":"all +0","page_div":"x/y","page_madd":"x*y+z non-fused; explicit fma variant tested separately","upper_triangle":"all +0","domain":"finite SPD inputs"},"limitations":["No official test package was provided; all datasets are self-set","The official image omits helper definitions; local explicit contracts are used","Generic AST VM is serial; parallel execution only for symbolically proven Cholesky patterns","This basic suite does not run general dense n=10000; see extended milestone record","Frontend does not support arbitrary C, pointer aliases, heap allocation, or helpers with control flow/mutable locals"]}
    (root/"test-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding="utf-8")
    print(json.dumps({"passed":True,"source_cases":len(cases),"oracle_comparisons":sum(len(c['runs']) for c in cases)+len(diagonal_runs)+len(repeated)+len(performance),"rejection_cases":len(rejection),"report":str(root/"test-report.json")},ensure_ascii=False))


if __name__ == "__main__": main()
