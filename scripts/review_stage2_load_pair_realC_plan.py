"""Independent lineage, matched-binary cohort and actual PE instruction audit."""
import hashlib,json,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/19-dynamic-graph';R=Path('G:/Hackathon-stage2-artifacts/project19/load-pair');D=R/'next-static-plan'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    manifest=read(D/'manifest.json');plan=read(D/'plan.json')
    assert sha(D/'manifest.json')=='a7bc23f45fca879f17eab5a2475950414ccdb85bbbf5901566979544d8893432'
    for path,r in manifest['files'].items():assert sha(D/path)==r['sha256'] and (D/path).stat().st_size==r['bytes']
    priorpath=P/'artifacts/stage2-vm-nested-budget/policy-cost/run-plan.json';prior=read(priorpath)
    assert plan['original_C_lineage_plan_sha256']==sha(priorpath)
    old={c['source']:c for c in prior['cases']};functional=plan['functional']['cases'];forced=plan['functional']['forced_cases'];cost=plan['cost']['cases']
    assert len(functional)==25 and len(forced)==2 and len(cost)==19
    assert len({c['hashes']['source.c'] for c in functional})==19
    for c in functional+forced+cost:
        b=old[c['source']]
        assert c['hashes']==b['hashes']==c['declared_original_C_hashes']
        for k in ('input_matrix_headers','reference_bytes','block'):assert c[k]==b[k]
        for name in ('source.c','program.meta','oracle.c','oracle.exe'):assert sha(c['paths'][name])==c['hashes'][name]
        for name in ('input.bin','oracle.bin'):
            assert c['paths'][name]==b['paths'][name] and Path(c['paths'][name]).stat().st_size==c['reference_bytes']
        command=c['runtime_command_common'];assert '--max-vm-steps' not in command and command[-2:]==['--vm-budget','fixed']
        assert c['backends']==['decoded-threaded','decoded-threaded-load-pair']
    assert sum(c['default_path_scope']=='genuine-default-VM' for c in cost)==18
    assert all(c['engine_requested']=='vm' for c in forced) and not set(c['identity'] for c in forced)&set(c['identity'] for c in cost)
    assert plan['cost']['rounds']==5 and plan['cost']['pairs']==95 and plan['cost']['records']==190
    exe=Path(plan['runtime']['path']);assert sha(exe)==plan['runtime']['sha256']=='a95a97d865f7be0942da06b9b35845fd540f88ed05aeaf0bea04d478fbb347e9'
    binary=exe.read_bytes();pe=struct.unpack_from('<I',binary,0x3c)[0];assert binary[pe:pe+4]==b'PE\0\0'
    count=struct.unpack_from('<H',binary,pe+6)[0];optional_size=struct.unpack_from('<H',binary,pe+20)[0];optional=pe+24;assert struct.unpack_from('<H',binary,optional)[0]==0x20b
    base=struct.unpack_from('<Q',binary,optional+24)[0];sections=[]
    for i in range(count):
        start=optional+optional_size+40*i;size,va,rawsize,raw=struct.unpack_from('<IIII',binary,start+8);sections.append((va,max(size,rawsize),raw))
    def actual_bytes(address,n):
        rva=address-base
        for va,size,raw in sections:
            if va<=rva<va+size:return binary[raw+rva-va:raw+rva-va+n]
        raise AssertionError(hex(address))
    observation=read(D/'machine-code-observation.json');checked=0;parsed={}
    for name in ('threaded','load-pair'):
        ops=[]
        for line in (D/(name+'-mangled.asm')).read_text(encoding='utf-8-sig').splitlines():
            m=re.match(r'\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*\t(.*)',line)
            if m:
                address=int(m[1],16);code=bytes.fromhex(m[2]);assert actual_bytes(address,len(code))==code;ops.append((address,m[3]));checked+=1
        indirect=[hex(a) for a,op in ops if re.match(r'jmp\s+\*',op)];assert indirect==observation[name]['indirect_jump_sites'] and len(indirect)==3
        parsed[name]=ops
    hot=[dict(address=hex(a),asm=op) for a,op in parsed['load-pair'] if 0x14001fb30<=a<=0x14001fc46]
    assert hot==observation['candidate_hot_pair_path'] and not any(re.match(r'jmp\s+\*',x['asm']) for x in hot)
    assert any(x['asm']=='cmp    $0x8000,%r10' for x in hot) and any(x['asm']=='add    $0x1,%r13' for x in hot)
    delta=observation['load-pair']['approximate_function_bytes']-observation['threaded']['approximate_function_bytes'];assert delta==1984
    result=dict(passed=True,static_only=True,plan_sha256=sha(D/'plan.json'),frozen_small_files=len(manifest['files']),true_C_sources=19,functional_records=54,cost_pairs=95,genuine_VM_pairs=90,native_control_pairs=5,actual_PE_instruction_lines_verified=checked,hot_pair_indirect_dispatch_removed=True,code_size_increase_bytes=1984,source_and_shape_cohort_unchanged=True,fresh_input_oracle_hash_required_at_actual_run=True,scope='Static lineage and actual-binary disassembly audit only. Prepare functional-only54 runner/filecapture/resources freeze first; no actual new functional/performance/default runs. Performance requires full-C correctness accepted first.')
    (ROOT/'outputs/stage2-root-load-pair-realC-plan.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
