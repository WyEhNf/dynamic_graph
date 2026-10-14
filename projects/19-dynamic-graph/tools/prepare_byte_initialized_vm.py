"""Second isolated factor: byte initialization flags instead of vector<bool>.

Program/scalar values and error timing are identical; initialization storage
grows from one bit to one byte per slot. Preserve first bounded-only evidence.
"""
import hashlib
import json
from pathlib import Path

BASE=Path('G:/Hackathon-stage2-artifacts/project19/20261013-bounded-stack')


def main():
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    src=BASE/'workspace/src/threaded_vm.cpp';cmake=BASE/'workspace/CMakeLists.txt'
    before={str(p):sha(p) for p in [src,cmake]}
    (BASE/'bounded-only-threaded_vm.cpp').write_bytes(src.read_bytes())
    (BASE/'bounded-only-CMakeLists.txt').write_bytes(cmake.read_bytes())
    text=src.read_text();needle='  std::vector<bool> initialized(metadata.slots,false);';assert text.count(needle)==1
    text=text.replace(needle,'''#ifdef CHOL_BYTE_INITIALIZED
  std::vector<unsigned char> initialized(metadata.slots,0);
#else
  std::vector<bool> initialized(metadata.slots,false);
#endif''')
    src.write_text(text)
    text=cmake.read_text()+'''
option(CHOL_BYTE_INITIALIZED "Use byte flags for scalar initialization" OFF)
if(CHOL_BYTE_INITIALIZED)
  target_compile_definitions(cholesky_core PRIVATE CHOL_BYTE_INITIALIZED=1)
endif()
''';cmake.write_text(text)
    (BASE/'byte-source-provenance.json').write_text(json.dumps({'base_sha256':before,
        'candidate_sha256':{str(p):sha(p) for p in [src,cmake]},'preparer_sha256':sha(Path(__file__)),
        'scope':'byte flag candidate, about 7/8 additional byte per Metadata scalar slot; no default change'},indent=2))
    print('Prepared byte flags; bounded-only source snapshot preserved')


if __name__=='__main__':main()
