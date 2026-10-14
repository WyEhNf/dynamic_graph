"""Bounded full-file compression, independent codecs, malformed streams and C."""
import argparse,hashlib,json,shutil,struct,subprocess,time,zlib
from pathlib import Path
from metadata_container import encode,decode,LIMIT
from evaluate_source import compile_oracle,run_runtime,exact_compare
import analyze_source

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protocol-only',action='store_true')
    parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--build-dir',type=Path,default=Path('build-stage2-zlib'))
    args=parser.parse_args();project=Path(__file__).resolve().parents[1];root=args.output_dir.resolve();root.mkdir(exist_ok=False,parents=True)
    build=args.build_dir.resolve();codec=build/'metadata_container_codec.exe';runtime=build/'cholesky_runtime.exe';started=time.perf_counter()
    def native(mode,data,name):
        ip=root/(name+'.input');op=root/(name+'.output');ip.write_bytes(data)
        run=subprocess.run([str(codec),mode,str(ip),str(op)],capture_output=True,text=True)
        return run,op
    rows=[];roundtrips=0
    frozen=project/'artifacts/stage2-smallest-metadata'
    for path in sorted(frozen.rglob('*.meta')):
        raw=path.read_bytes();compressed=encode(raw);label=path.parent.name+'-'+path.stem
        # Official native decoder must reproduce every byte, not just parser fields.
        run,op=native('decode',compressed,label+'-decode');assert run.returncode==0 and op.read_bytes()==raw
        run,op=native('encode',raw,label+'-encode');assert run.returncode==0 and decode(op.read_bytes())==raw and zlib.decompress(op.read_bytes()[16:])==raw
        run,op=native('parse',compressed,label+'-parse');assert run.returncode==0
        rows.append({'source':path.parent.name,'file':str(path),'raw_sha256':sha(path),'raw_bytes':len(raw),'container_bytes':len(compressed),'container_sha256':hashlib.sha256(compressed).hexdigest()});roundtrips+=1
    anchor=(frozen/'scalar/minimum.meta').read_bytes()
    modes=[]
    for level,strategy in ((0,zlib.Z_DEFAULT_STRATEGY),(1,zlib.Z_DEFAULT_STRATEGY),(6,zlib.Z_DEFAULT_STRATEGY),(9,zlib.Z_DEFAULT_STRATEGY),(9,zlib.Z_FIXED),(9,zlib.Z_HUFFMAN_ONLY),(9,zlib.Z_RLE)):
        compressor=zlib.compressobj(level,zlib.DEFLATED,15,8,strategy);payload=compressor.compress(anchor)+compressor.flush()
        data=b'DYNCHZ01'+struct.pack('<II',len(anchor),len(payload))+payload
        run,op=native('decode',data,f'mode-{level}-{strategy}');assert run.returncode==0 and op.read_bytes()==anchor
        modes.append({'level':level,'strategy':strategy,'bytes':len(data)})
    legal_boundary=b'a'*LIMIT;data=encode(legal_boundary)
    run,op=native('decode',data,'legal-raw-limit');assert run.returncode==0 and sha(op)==hashlib.sha256(legal_boundary).hexdigest()
    assert decode(data)==legal_boundary
    # Exact payload bound using standard stored DEFLATE blocks, not padding a stream.
    length=LIMIT-1300
    for _ in range(4):
        payload=zlib.compress(b'x'*length,0)
        if len(payload)==LIMIT:break
        length+=LIMIT-len(payload)
    assert len(payload)==LIMIT
    data=b'DYNCHZ01'+struct.pack('<II',length,len(payload))+payload
    run,op=native('decode',data,'legal-payload-limit');assert run.returncode==0 and op.read_bytes()==b'x'*length and decode(data)==b'x'*length
    run,op=native('decode',encode(b'x'),'legal-one-byte');assert run.returncode==0 and op.read_bytes()==b'x'
    bits_goldens=[('+0.0',0),('-0.0',0x8000000000000000),('5e-324',1),('2.2250738585072014e-308',0x0010000000000000),('1.7976931348623157e308',0x7fefffffffffffff),('9007199254740993.0',0x4340000000000000)]
    for schema in (2,3):
        fields=f'DYNCHOL {schema}\nalgorithm=ast_vm_v2\narithmetic=fp64_source_order_no_implicit_fma\ndependencies=source_control_flow\noptimized=none\nslots=1\nshape_slot=0\nblock_slot=-1\n'+('bytecode_encoding=base36_opcode_v1\n' if schema==3 else '')+'PROGRAM\n'
        for i,(token,bits) in enumerate(bits_goldens):
            raw=(fields+('0 ' if schema==3 else 'CONST ')+token+'\n'+('W' if schema==3 else 'RETURN')+'\n').encode()
            run,op=native('parsebits',encode(raw),f'bits-{schema}-{i}');assert run.returncode==0 and op.read_bytes()==struct.pack('<Q',bits)
    # Inner legacy schema and malformed inner schemas use the unmodified parser.
    legacy=b'DYNCHOL 1\nalgorithm=cholesky_column_v1\narithmetic=fp64_ascending_k_no_fma\ndependencies=column_barrier_diagonal_then_rows\n'
    run,op=native('parse',encode(legacy),'legacy1');assert run.returncode==0
    good=encode(anchor);payload=good[16:]
    def wrap(payload,raw=len(anchor)):return b'DYNCHZ01'+struct.pack('<II',raw,len(payload))+payload
    invalid=[('short',good[:15]),('unknown-version',b'DYNCHZ02'+good[8:]),('raw-zero',wrap(payload,0)),('raw-over-limit',wrap(payload,LIMIT+1)),('raw-uint-max',wrap(payload,0xffffffff)),('payload-over-limit',good[:12]+struct.pack('<I',LIMIT+1)+payload),('payload-zero',good[:12]+struct.pack('<I',0)+payload),('raw-too-small',wrap(payload,len(anchor)-1)),('raw-too-large',wrap(payload,len(anchor)+1)),('trailing-file',good+b'x'),('trailing-stream',wrap(payload+b'x')),('concatenated',wrap(payload+payload)),('bad-adler',wrap(payload[:-1]+bytes([payload[-1]^1]))),('bad-cmf',wrap(bytes([payload[0]^1])+payload[1:])),('bad-flg',wrap(payload[:1]+bytes([payload[1]^1])+payload[2:])),('invalid-deflate-btype',wrap(b'\x78\x9c\x07\x00\x00\x00\x01')),('raw-deflate',wrap(payload[2:-4]))]
    gzip=zlib.compressobj(wbits=31);invalid.append(('gzip',wrap(gzip.compress(anchor)+gzip.flush())))
    dictionary=zlib.compressobj(zdict=b'DYNCHOL');invalid.append(('dictionary',wrap(dictionary.compress(anchor)+dictionary.flush())))
    for length in (0,1,2,5,10,len(payload)//2,len(payload)-1):invalid.append((f'truncated-{length}',wrap(payload[:length])))
    rejections=[]
    for label,data in invalid:
        run,op=native('decode',data,'reject-'+label);assert run.returncode!=0 and not op.exists(),label
        try:decode(data)
        except ValueError:pass
        else:raise AssertionError('Python accepted '+label)
        rejections.append({'label':label,'error':run.stderr.strip(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    inner_reject=[]
    for label,raw in [('nested',good),('unknown-inner',anchor.replace(b'DYNCHOL 3',b'DYNCHOL 4',1)),('duplicate-field',anchor.replace(b'PROGRAM',b'slots=1\nPROGRAM',1)),('bad-instruction',anchor+b'Z\n')]:
        run,op=native('parse',encode(raw),'inner-reject-'+label);assert run.returncode!=0 and not op.exists(),label
        inner_reject.append({'label':label,'error':run.stderr.strip()})
    # Ordinary frozen release deliberately rejects opt-in container.
    ip=root/'ordinary-reject.meta';ip.write_bytes(good)
    run=subprocess.run([str(project/'build/cholesky_runtime.exe'),'--metadata',str(ip),'--input',str(frozen/'scalar/dense-input.bin'),'--output',str(root/'ordinary-reject.bin')],capture_output=True,text=True)
    assert run.returncode!=0 and 'unsupported metadata schema' in run.stderr and not (root/'ordinary-reject.bin').exists()
    report={'passed':False,'runtime_sha256':sha(runtime),'codec_sha256':sha(codec),'ordinary_runtime_sha256':sha(project/'build/cholesky_runtime.exe'),'roundtrips':roundtrips,'files':rows,'standard_python_encoder_modes':modes,'legal_raw_boundary':LIMIT,'legal_payload_boundary':LIMIT,'legal_one_byte':True,'native_ieee754_bit_goldens':12,'container_rejections':rejections,'inner_parser_rejections':inner_reject,'legacy1':True,'ordinary_disabled_rejection':True,'runs':[],'sources':[],'metadata_loading_cost':'metadata_read_ms includes file read + bounded inflation + original parser; separate from compute_ms','scope':'whole Metadata/full source C output files; uncompressed selector preserved; compressed selector uses final bytes; opt-in'}
    if not args.protocol_only:
        functions={'scalar':'cholesky_reference','page':'cholesky','blocked':'cholesky_blocked','generic':'transform','negative-zero':'zeros','noop':'noop'}
        for label,function in functions.items():
            folder=root/label;folder.mkdir();source=folder/'source.c';shutil.copyfile(frozen/label/'source.c',source)
            oracle=compile_oracle(source,function,folder,'E:/mingw64/bin/gcc.exe',label=='blocked')
            # Exercise actual frontend flag and compare unchanged bytes after inflation.
            cli=folder/'cli.meta';analysis=analyze_source.analyze(source,cli,'C:/Program Files/LLVM/bin/clang.exe',function,smallest_metadata=True,compress_metadata=True)
            expected=min(((schema,mode,(frozen/label/f'{schema}-{mode}.meta').read_bytes())for schema in (2,3)for mode in ('dag','table','expanded')),key=lambda item:(len(encode(item[2])),item[0],('dag','table','expanded').index(item[1])))
            assert decode(cli.read_bytes())==expected[2]
            default=folder/'default.meta';analyze_source.analyze(source,default,'C:/Program Files/LLVM/bin/clang.exe',function)
            assert default.read_bytes()==(frozen/label/'2-dag.meta').read_bytes()
            for family in ('dense','diagonal-signed-zero'):
                ip=folder/(family+'-input.bin');shutil.copyfile(frozen/label/(family+'-input.bin'),ip)
                ref=folder/(family+'-oracle.bin');subprocess.run([str(oracle),str(ip),str(ref),'7'],check=True)
                for variant in ('2-dag','3-table','minimum'):
                    meta=folder/(variant+'.meta');meta.write_bytes(encode((frozen/label/(variant+'.meta')).read_bytes()))
                    for engine in ('vm','tiled'):
                        output=folder/(family+'-'+variant+'-'+engine+'.bin');metrics=run_runtime(runtime,meta,ip,output,engine=engine,threads=1,block=7,tile_size=7)
                        report['runs'].append({'source':label,'family':family,'variant':variant,'engine':engine,'source_sha256':sha(source),'oracle_sha256':sha(oracle),'input_sha256':sha(ip),'reference_sha256':sha(ref),'metadata_sha256':sha(meta),**metrics,**exact_compare(ref,output)})
            report['sources'].append({'label':label,'source_sha256':sha(source),'oracle_sha256':sha(oracle),'analysis':analysis,'default_metadata_bytes_identical':True})
            print(json.dumps({'source':label,'runs':sum(row['source']==label for row in report['runs'])}),flush=True)
    report.update(passed=True,comparisons=len(report['runs']),wall_seconds=time.perf_counter()-started)
    (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ('passed','roundtrips','comparisons','wall_seconds')}),flush=True)

if __name__=='__main__':main()
