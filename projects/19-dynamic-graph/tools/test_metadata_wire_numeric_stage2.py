"""Execute boundary constants; compare complete binary files with bit goldens."""
import hashlib,json,struct,subprocess,shutil
from pathlib import Path

def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-metadata-wire-numeric-bits'
    if root.exists():raise SystemExit('Refusing to overwrite numeric evidence')
    root.mkdir();runtime=project/'artifacts/stage2-metadata-wire/candidate.exe'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    shutil.copyfile(__file__,root/'test_metadata_wire_numeric_stage2.py')
    ip=root/'input.bin';ip.write_bytes(struct.pack('<II9d',1,3,*([1.0]*9)))
    fields='algorithm=ast_vm_v2\narithmetic=fp64_source_order_no_implicit_fma\ndependencies=source_control_flow\noptimized=none\nslots=1\nshape_slot=0\nblock_slot=-1\n'
    tokens=('-0.0','+0.0','5e-324','1e-320','2.2250738585072014e-308','1.7976931348623157e308','-1.7976931348623157e308')
    rows=[]
    for schema in (2,3):
        for i,token in enumerate(tokens):
            # Five instructions write one original numeric token at output[0].
            program=('0 0\n0 '+token+'\n5 1\n0 0\nW\n') if schema==3 else ('CONST 0\nCONST '+token+'\nWRITE 1\nCONST 0\nRETURN\n')
            meta=root/f'{schema}-{i}.meta';meta.write_text('DYNCHOL '+str(schema)+'\n'+fields+('bytecode_encoding=base36_opcode_v1\n' if schema==3 else '')+'PROGRAM\n'+program)
            output=root/f'{schema}-{i}.bin'
            run=subprocess.run([str(runtime),'--metadata',str(meta),'--input',str(ip),'--output',str(output),'--engine','vm'],capture_output=True,text=True,check=True)
            expected=struct.pack('<II9d',1,3,float(token),*([0.0]*8))
            assert output.read_bytes()==expected
            rows.append({'schema':schema,'token':token,'metadata_sha256':sha(meta),'output_sha256':sha(output),'byte_identical':True,'bits':struct.pack('<d',float(token)).hex(),'metrics':json.loads(run.stdout)})
    report={'passed':True,'runtime_sha256':sha(runtime),'test_source_sha256':sha(Path(__file__)),'runtime_comparisons':14,'scope':'Seven finite boundary constants × two wire schemas, exact complete output with independent struct.pack bit goldens','rows':rows}
    (root/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':True,'comparisons':14}))

if __name__=='__main__':main()
