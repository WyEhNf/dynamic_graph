"""Check actual six-format final Metadata selections without executing native code."""
import hashlib
import json
import struct
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/19-dynamic-graph'
DIR = PROJECT / 'artifacts/stage2-compressed-smallest'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


report = json.loads((DIR / 'report.json').read_text(encoding='utf-8'))
manifest = json.loads((DIR / 'manifest.json').read_text(encoding='utf-8'))
assert manifest['status'] == 'verified_final_container_byte_minimum'
assert sha(DIR / 'report.json') == manifest['report_sha256']
assert sha(Path(manifest['prior_immutable_manifest'])) == manifest['prior_manifest_sha256']
assert report['passed'] and report['comparisons'] == 24 and report['whole_container_candidates'] == 36
assert report['cli_combination_passed'] and report['conflicting_cli_options_rejected'] == 3
assert sha(PROJECT / 'build/cholesky_runtime.exe') == manifest['ordinary_runtime_sha256']
assert sha(PROJECT / 'artifacts/stage2-metadata-zlib/cholesky_runtime.exe') == manifest['runtime_sha256']
checked = 0
selections = []
for source in report['sources']:
    assert source['compilation_counts'] == dict(ast=1, llvm_ir=1)
    assert source['uncompressed_default_and_minimum_unchanged']
    assert source['explicit_single_format_preserved']
    assert len(source['candidates']) == 6
    formats = set()
    for candidate in source['candidates']:
        path = Path(candidate['path'])
        encoded = path.read_bytes()
        assert len(encoded) == candidate['metadata_bytes'] and sha(path) == candidate['sha256']
        assert encoded[:8] == b'DYNCHZ01'
        raw_size, compressed_size = struct.unpack('<II', encoded[8:16])
        assert compressed_size == len(encoded) - 16 and raw_size == candidate['uncompressed_metadata_bytes']
        stream = zlib.decompressobj()
        raw = stream.decompress(encoded[16:], raw_size + 1) + stream.flush()
        assert stream.eof and not stream.unused_data and not stream.unconsumed_tail
        assert len(raw) == raw_size
        assert hashlib.sha256(raw).hexdigest() == candidate['uncompressed_metadata_sha256']
        key = candidate['metadata_schema'], candidate['symbolic_format']
        formats.add(key)
        checked += 1
    assert formats == {(schema, fmt) for schema in (2,3) for fmt in ('dag','table','expanded')}
    best = min(source['candidates'], key=lambda c: (c['metadata_bytes'],c['metadata_schema'],
                                                    ('dag','table','expanded').index(c['symbolic_format'])))
    selection = source['selection']
    assert all(best[k] == selection[k] for k in selection)
    assert len(source['runs']) == 4 and all(r['byte_identical'] for r in source['runs'])
    selections.append(dict(source=source['source'],before=source['prior_compressed_minimum_bytes'],
                           after=selection['metadata_bytes'],format=f"{selection['metadata_schema']}-{selection['symbolic_format']}"))
assert checked == 36 and len(selections) == 6
result = dict(reviewed_unix=time.time(),passed=True,independently_decoded_candidates=checked,
              original_c_full_file_records=24,actual_final_byte_selections=selections,
              method='Root standard Python zlib decoded all saved complete native-format containers and independently checked exact size/SHA and six-format tie rule. Existing actual original-C byte-comparison records inspected; no duplicate C run.',
              limitation='Minimum of the six implemented encodings at fixed compression settings; not a minimum over all possible Metadata encodings or an official score claim.',
              report_sha256=sha(DIR/'report.json'),manifest_sha256=sha(DIR/'manifest.json'))
destination = ROOT / 'outputs/stage2-root-compressed-choice-review.json'
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,decoded=checked,selections=selections),ensure_ascii=False))
