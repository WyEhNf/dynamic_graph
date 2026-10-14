"""Read frozen Metadata, measure full bytes plus a specified 16-byte container."""
import hashlib,json,struct,zlib
from pathlib import Path

def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'artifacts/stage2-metadata-zlib'
    root.mkdir(exist_ok=False)
    rows=[]
    for folder in ('stage2-smallest-metadata','stage2-metadata-wire'):
        for path in sorted((project/'artifacts'/folder).rglob('*.meta')):
            data=path.read_bytes();payload=zlib.compress(data,9)
            container=b'DYNCHZ01'+struct.pack('<II',len(data),len(payload))+payload
            assert zlib.decompress(container[16:])==data
            rows.append({'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'zlib_stream_bytes':len(payload),'container_header_bytes':16,'zlib_header_and_adler_bytes':6,'container_bytes':len(container),'delta_bytes':len(container)-len(data)})
    small=[]
    for data in (b'',b'DYNCHOL 1\n',bytes(range(256))):
        small.append({'hex':data.hex(),'bytes':len(data),'container_bytes':16+len(zlib.compress(data,9)),'scope':'container expansion diagnostic, not accepted Metadata'})
    report={'scope':'Whole frozen Metadata; no byte/graph/task/PROGRAM deletion; proposed DYNCHZ01 + LE uint32 raw/payload lengths + RFC1950 stream','python_zlib_compile':zlib.ZLIB_VERSION,'python_zlib_runtime':zlib.ZLIB_RUNTIME_VERSION,'level':9,'rows':rows,'tiny_non_metadata_expansion_diagnostics':small,'primary_refs':['https://www.rfc-editor.org/rfc/rfc1950','https://www.rfc-editor.org/rfc/rfc1951','https://zlib.net/','https://zlib.net/manual.html']}
    (root/'size-probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'files':len(rows),'minimum_cases':[row for row in rows if Path(row['path']).name=='minimum.meta'],'tiny_diagnostics':small},indent=2))

if __name__=='__main__':main()
