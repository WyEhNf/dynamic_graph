"""Compile a supported C function's actual Clang AST to dynamic-shape bytecode.

No source-body whitelist, source hash dispatch, or function-name dispatch is used.
The bytecode is executable for arbitrary supported loop/array arithmetic, including
blocked loops. A separate semantic proof recognizes scalar Cholesky for scheduling.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import tempfile
from c_frontend import Compiler, walk
from symbolic_metadata import encode_symbols,decode_symbols,encode_record_table,decode_record_table
from metadata_wire import encode_instruction,decode_instruction
from packed_symbolic_metadata import pack_symbols,unpack_symbols


def _clang_version_from_verbose(stderr):
    """Reuse only an unambiguous driver version header, never source IR ident.

    Wrappers may prepend diagnostics or print another version. In those cases
    keep the existing independent --version query instead of guessing.
    """
    lines=stderr.splitlines()
    version=re.compile(r'^(?:(?:Apple|Ubuntu|Debian) )?clang version \S.*$')
    if len(lines)<4 or not version.fullmatch(lines[0]): return None
    if sum(bool(version.fullmatch(line)) for line in lines)!=1: return None
    if not re.fullmatch(r'Target: \S+',lines[1]): return None
    if not re.fullmatch(r'Thread model: \S+',lines[2]): return None
    if not re.fullmatch(r'InstalledDir: \S.*',lines[3]): return None
    if any(ord(character)<32 for line in lines[:4] for character in line): return None
    return lines[0]


def _dependency_paths(text):
    """Read the one Make dependency rule emitted with our fixed -MT target."""
    text=re.sub(r'\\\r?\n','',text)
    target,separator,body=text.partition(':')
    if not separator or target.strip()!='dynchol_prepared': raise ValueError('unexpected Clang dependency rule')
    paths=[];token=[];index=0
    while index<len(body):
        character=body[index]
        if character=='\\' and index+1<len(body) and body[index+1] in ' \t#\\:':
            index+=1;token.append(body[index])
        elif character=='$' and index+1<len(body) and body[index+1]=='$':
            index+=1;token.append('$')
        elif character.isspace():
            if token: paths.append(Path(''.join(token)).resolve());token=[]
        else:token.append(character)
        index+=1
    if token:paths.append(Path(''.join(token)).resolve())
    if not paths:raise ValueError('Clang did not record source dependencies')
    return tuple(dict.fromkeys(paths))


class PreparedSource:
    """Explicit live batch snapshot: parse once, emit many, never cache on disk.

    Source/include hashes are checked before every reuse. Compiler identity is
    recorded by the actual AST invocation; LLVM IR is produced once on demand.
    A changed source or header requires constructing a new PreparedSource.
    """
    def __init__(self,source,clang='clang'):
        self.source=Path(source).resolve();self.clang=clang
        resolved=shutil.which(clang)
        if resolved is None:raise ValueError(f'cannot resolve compiler: {clang}')
        self._compiler_path=Path(resolved).resolve()
        info=self._compiler_path.stat();self._compiler_stamp=(info.st_size,info.st_mtime_ns)
        self._environment={key:os.environ.get(key) for key in ('PATH','INCLUDE','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','OBJC_INCLUDE_PATH','SDKROOT')}
        self.source_sha256=hashlib.sha256(self.source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='dynchol-frontend-') as directory:
            dependencies=Path(directory)/'source.d'
            discovery=subprocess.run([clang,'-std=c11','-M','-MF',str(dependencies),'-MT','dynchol_prepared',str(self.source)],capture_output=True,text=True)
            if discovery.returncode:raise ValueError(discovery.stderr)
            paths=_dependency_paths(dependencies.read_text(encoding='utf-8'))
            if self.source not in paths:raise ValueError('Clang source missing from dependency rule')
            self.dependencies={path:hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
            if self.dependencies[self.source]!=self.source_sha256:raise ValueError('source changed while preparing frontend')
            run=subprocess.run([clang,'-v','-std=c11','-MD','-MF',str(dependencies),'-MT','dynchol_prepared','-Xclang','-ast-dump=json','-fsyntax-only',str(self.source)],capture_output=True,text=True)
            if run.returncode:raise ValueError(run.stderr)
            self.ast=json.loads(run.stdout)
            if set(_dependency_paths(dependencies.read_text(encoding='utf-8')))!=set(paths):raise ValueError('source dependency set changed while preparing frontend')
        self.validate()
        self.clang_version=_clang_version_from_verbose(run.stderr)
        if self.clang_version is None:self.clang_version=subprocess.run([clang,'--version'],capture_output=True,text=True).stdout.splitlines()[0]
        self._ir=None

    def validate(self):
        try:info=self._compiler_path.stat()
        except OSError as error:raise ValueError('prepared source compiler is unavailable') from error
        if (info.st_size,info.st_mtime_ns)!=self._compiler_stamp:raise ValueError('prepared source compiler changed')
        if any(os.environ.get(key)!=value for key,value in self._environment.items()):raise ValueError('prepared source compiler environment changed')
        for path,digest in self.dependencies.items():
            try:current=hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as error:raise ValueError(f'prepared source dependency is unavailable: {path}') from error
            if current!=digest:
                raise ValueError(f'prepared source dependency changed: {path}')

    def llvm_ir(self):
        self.validate()
        if self._ir is None:
            # Clang's Windows stdout adds CRLF; a real output file preserves
            # exactly the audit bytes emitted by the existing one-shot path.
            with tempfile.TemporaryDirectory(prefix='dynchol-ir-') as directory:
                output=Path(directory)/'source.ll'
                dependencies=Path(directory)/'source.d'
                subprocess.run([self.clang,'-std=c11','-MD','-MF',str(dependencies),'-MT','dynchol_prepared','-O0','-ffp-contract=off','-S','-emit-llvm',str(self.source),'-o',str(output)],check=True)
                if set(_dependency_paths(dependencies.read_text(encoding='utf-8')))!=set(self.dependencies):raise ValueError('source dependency set changed while emitting IR')
                ir=output.read_bytes()
            self.validate()
            self._ir=ir
        return self._ir

    def emit(self,output,function='cholesky_reference',**options):
        return analyze(self.source,output,self.clang,function,prepared=self,**options)


def analyze(source, output, clang="clang", function="cholesky_reference", symbolic_format="dag", include_provenance=False,compact_bytecode=True,metadata_schema=2,smallest_metadata=False,compress_metadata=False,metadata_newlines="lf",emit_ir=True,prepared=None):
    if metadata_newlines not in ('native','lf'): raise ValueError('metadata_newlines must be native or lf')
    newline='\n' if metadata_newlines=='lf' else os.linesep
    if metadata_schema not in (2,3): raise ValueError('metadata schema must be 2 or 3')
    if metadata_schema==3 and not compact_bytecode: raise ValueError('schema 3 requires canonical compact arguments')
    if symbolic_format not in ('dag','table','expanded','packed'): raise ValueError('symbolic format must be dag, table, expanded or packed')
    if smallest_metadata and (metadata_schema!=2 or symbolic_format!='dag' or not compact_bytecode):
        raise ValueError('smallest metadata is mutually exclusive with explicit schema/format/full arguments')
    source = Path(source).resolve()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if prepared is None:
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()
        run=subprocess.run([clang,'-v','-std=c11','-Xclang','-ast-dump=json','-fsyntax-only',str(source)],capture_output=True,text=True)
        if run.returncode:raise ValueError(run.stderr)
        clang_version=_clang_version_from_verbose(run.stderr)
        ast=json.loads(run.stdout)
    else:
        if prepared.source!=source or prepared.clang!=clang:raise ValueError('prepared source/compiler does not match analysis request')
        prepared.validate()
        clang_version=prepared.clang_version
        ast=prepared.ast
        source_sha256=prepared.source_sha256
    definitions = [n for n in walk(ast) if n.get("kind") == "FunctionDecl" and n.get("name") == function and any(c.get("kind") == "CompoundStmt" for c in n.get("inner", []))]
    if len(definitions) != 1:
        raise ValueError("exactly one requested function definition is required")
    function_declarations={n['id']:n for n in walk(ast)if n.get('kind')=='FunctionDecl'}
    helper_definitions={key:n for key,n in function_declarations.items()if any(c.get('kind')=='CompoundStmt'for c in n.get('inner',[]))}
    # Clang call sites preceding a definition reference its prototype identity.
    # Follow actual redeclaration links, never resolve helpers by their names.
    for definition in list(helper_definitions.values()):
        previous=definition.get('previousDecl')
        while previous:
            helper_definitions[previous]=definition
            previous=function_declarations.get(previous,{}).get('previousDecl')
    compiler = Compiler(definitions[0], helper_definitions)
    compiler.compile()
    ir_path=output.with_suffix('.ll') if emit_ir else None
    if emit_ir:
        if prepared is None:subprocess.run([clang,'-std=c11','-O0','-ffp-contract=off','-S','-emit-llvm',str(source),'-o',str(ir_path)],check=True)
        else:ir_path.write_bytes(prepared.llvm_ir())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=source_sha256:raise ValueError('source changed during analysis')
    # Lossless shared expressions keep the full symbolic source graph in Metadata
    # while avoiding repeated row-major index/reduction subtrees.
    pool,loops,accesses=encode_symbols(compiler.loops,compiler.accesses)
    if decode_symbols(pool,loops,accesses)!=(compiler.loops,compiler.accesses):raise ValueError('symbolic metadata round-trip failed')
    loop_table,access_table=encode_record_table(loops),encode_record_table(accesses)
    if (decode_record_table(loop_table),decode_record_table(access_table))!=(loops,accesses):
        raise ValueError('symbolic record table round-trip failed')
    dumps=lambda value:json.dumps(value,separators=(',',':'))
    symbolic_fields={
        'dag':["symbolic_encoding=expr_dag_v1","symbolic_expr_pool="+dumps(pool),"symbolic_loops="+dumps(loops),"symbolic_accesses="+dumps(accesses)],
        'table':["symbolic_encoding=expr_dag_record_table_v1","symbolic_expr_pool="+dumps(pool),"symbolic_loop_table="+dumps(loop_table),"symbolic_access_table="+dumps(access_table)],
        'expanded':["symbolic_encoding=expr_tree_v1","symbolic_loops="+dumps(compiler.loops),"symbolic_accesses="+dumps(compiler.accesses)]}
    if symbolic_format=='packed' or smallest_metadata:
        ops,packed_pool,packed_loops,packed_accesses=pack_symbols(pool,loops,accesses)
        if unpack_symbols(ops,packed_pool,packed_loops,packed_accesses)!=(pool,loops,accesses):
            raise ValueError('packed symbolic metadata round-trip failed')
        symbolic_fields['packed']=["symbolic_encoding=expr_dag_packed_records_v1","symbolic_expr_ops="+dumps(ops),"symbolic_expr_pool="+dumps(packed_pool),"symbolic_loop_records="+dumps(packed_loops),"symbolic_access_records="+dumps(packed_accesses)]
    task_fields=[]
    if compiler.optimized!="none":
        task_fields=["task_schema=ordered_cholesky_tiles_v1","task_dependences="+dumps({"tiles":"ceil(N/B)","P(k)":["U(k,k,k-1)"],"T(m,k)":["P(k)","U(m,k,k-1)"],"U(m,h,k)":["T(m,k)","T(h,k)","U(m,h,k-1)"],"domains":["0<=k<tiles","k<m<tiles","k<h<=m<tiles"],"arithmetic":"each output cell accumulates source columns in ascending order"})]
    required={'CONST','LOAD','STORE','UNINIT','READ','WRITE','JUMP','JZ','JNZ'}
    instructions=[instruction[0]if compact_bytecode and instruction[0]not in required else " ".join(map(str,instruction))for instruction in compiler.code]
    encoded=None
    if metadata_schema==3 or smallest_metadata:
        encoded=[encode_instruction(line) for line in instructions]
        if [decode_instruction(line) for line in encoded]!=instructions: raise ValueError('bytecode wire round-trip failed')
    def render(schema,mode):
        fields=[f"DYNCHOL {schema}","algorithm=ast_vm_v2","arithmetic=fp64_source_order_no_implicit_fma","dependencies=source_control_flow",f"optimized={compiler.optimized}",f"slots={len(compiler.slots)}",f"shape_slot={compiler.shape_slot}",f"block_slot={compiler.block_slot}"]
        if schema==3:fields+=['bytecode_encoding=base36_opcode_v1']
        if include_provenance:fields+=[f"source_sha256={source_sha256}",f"function={function}"]
        fields+=symbolic_fields[mode]+task_fields+["PROGRAM"]+(encoded if schema==3 else instructions)
        return (newline.join(fields)+newline).encode('utf-8')
    candidates=[]
    compressed_candidates={}
    if compress_metadata:
        from metadata_container import encode
    if smallest_metadata:
        for schema in (2,3):
            for mode in ('dag','table','expanded','packed'):
                payload=render(schema,mode)
                final_payload=encode(payload) if compress_metadata else payload
                candidate={'metadata_schema':schema,'symbolic_format':mode,'metadata_bytes':len(final_payload),'sha256':hashlib.sha256(final_payload).hexdigest()}
                if compress_metadata:
                    compressed_candidates[schema,mode]=final_payload
                    candidate.update(uncompressed_metadata_bytes=len(payload),uncompressed_metadata_sha256=hashlib.sha256(payload).hexdigest())
                candidates.append(candidate)
        winner=min(candidates,key=lambda item:(item['metadata_bytes'],item['metadata_schema'],('dag','table','expanded','packed').index(item['symbolic_format'])))
        metadata_schema,symbolic_format=winner['metadata_schema'],winner['symbolic_format']
    # Score the exact emitted UTF-8 bytes using the selected newline convention.
    raw_metadata=render(metadata_schema,symbolic_format)
    if compress_metadata:
        output.write_bytes(compressed_candidates[metadata_schema,symbolic_format] if smallest_metadata else encode(raw_metadata))
    else:
        output.write_bytes(raw_metadata)
    report = {
        "source": str(source), "function": function,"source_sha256":source_sha256,"metadata_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
        "clang": clang_version if clang_version is not None else subprocess.run([clang, "--version"], capture_output=True, text=True).stdout.splitlines()[0],
        "metadata_bytes": output.stat().st_size, "instructions": len(compiler.code),
        "symbolic_encoding":{'dag':'expr_dag_v1','table':'expr_dag_record_table_v1','expanded':'expr_tree_v1','packed':'expr_dag_packed_records_v1'}[symbolic_format],"symbolic_expressions":len(pool),"provenance_inline":include_provenance,
        "compact_bytecode":compact_bytecode,
        "metadata_schema":metadata_schema,"bytecode_encoding":'base36_opcode_v1' if metadata_schema==3 else 'named_opcodes',
        "metadata_newlines":metadata_newlines,"smallest_metadata":smallest_metadata,"encoding_candidates":candidates,
        "minimum_cost_metric":'final_container_bytes' if compress_metadata else 'utf8_file_bytes',"minimum_tie_rule":'schema2 before schema3, then dag/table/expanded/packed',
        "compressed_metadata":compress_metadata,"uncompressed_metadata_bytes":len(raw_metadata),"uncompressed_metadata_sha256":hashlib.sha256(raw_metadata).hexdigest(),
        "ir": str(ir_path) if emit_ir else None, "optimized": compiler.optimized,
        "loops": compiler.loops, "accesses": compiler.accesses,
        "dependency_policy": "Preserve source control flow and per-element arithmetic order. Proven left/right-looking Cholesky and exact contiguous tile wrappers execute a parameterized tile DAG; all other programs use source-order VM.",
        "support": "Clang AST scalar int/double, 1D double arrays, for/while/if, arithmetic, comparisons, sqrt/fabs/fmin/fmax/fma, pure scalar helper inlining; unsupported constructs fail closed",
    }
    if not emit_ir:report['ir_status']='omitted-explicitly'
    output.with_suffix(".analysis.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--function", default="cholesky_reference")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument('--symbolic-format',choices=('dag','table','expanded','packed'))
    parser.add_argument('--provenance-inline',action='store_true',help='also carry source SHA/function in executable Metadata; always preserved in analysis.json')
    parser.add_argument('--full-bytecode-args',action='store_true',help='emit explicit zero arguments for older Runtime binaries')
    parser.add_argument('--metadata-schema',type=int,choices=(2,3),help='schema 3 is opt-in and requires the updated Runtime; default 2')
    parser.add_argument('--smallest-metadata',action='store_true',help='choose the smallest equivalent schema2/3 × dag/table/expanded/packed; requires updated Runtime')
    parser.add_argument('--metadata-newlines',choices=('native','lf'),default='lf',help='LF is canonical by default; native restores the host newline convention')
    parser.add_argument('--compress-metadata',action='store_true',help='wrap complete selected Metadata in DYNCHZ01; requires CHOL_COMPRESSED_METADATA=ON Runtime')
    parser.add_argument('--skip-ir',action='store_true',help='explicit Metadata-only analysis: retain complete AST graph and compiler provenance, omit optional LLVM audit file')
    args = parser.parse_args()
    if args.smallest_metadata and (args.symbolic_format is not None or args.metadata_schema is not None or args.full_bytecode_args):
        parser.error('--smallest-metadata is mutually exclusive with --symbolic-format, --metadata-schema and --full-bytecode-args')
    try:
        print(json.dumps(analyze(args.source, args.output, args.clang, args.function,args.symbolic_format or 'dag',args.provenance_inline,not args.full_bytecode_args,args.metadata_schema or 2,args.smallest_metadata,args.compress_metadata,args.metadata_newlines,not args.skip_ir), ensure_ascii=False))
    except (ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
