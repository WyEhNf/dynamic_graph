"""Isolated pointer-to-decoded-instruction experiment (no opcode changes)."""
import hashlib
import json
from pathlib import Path

BASE=Path('G:/Hackathon-stage2-artifacts/project19/20261013-bounded-stack')


def main():
    src=BASE/'workspace/src/threaded_vm.cpp';cmake=BASE/'workspace/CMakeLists.txt'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={str(p):sha(p) for p in [src,cmake]}
    (BASE/'directtargets-threaded_vm.cpp').write_bytes(src.read_bytes())
    (BASE/'directtargets-CMakeLists.txt').write_bytes(cmake.read_bytes())
    text=src.read_text()
    needle='  DecodedInstruction instruction{};'
    assert text.count(needle)==1
    text=text.replace(needle,'''#ifdef CHOL_INSTRUCTION_POINTER
  const DecodedInstruction* instruction_pointer=nullptr;
#define instruction (*instruction_pointer)
#define FETCH_INSTRUCTION() instruction_pointer=&decoded[pc]
#else
  DecodedInstruction instruction{};
#define FETCH_INSTRUCTION() instruction=decoded[pc]
#endif''')
    needle='  instruction=decoded[pc];++pc;'
    assert text.count(needle)==1
    text=text.replace(needle,'  FETCH_INSTRUCTION();++pc;')
    text=text.replace('#undef JUMP_TARGET','#undef JUMP_TARGET\n#undef FETCH_INSTRUCTION\n#ifdef CHOL_INSTRUCTION_POINTER\n#undef instruction\n#endif')
    src.write_text(text)
    cmake.write_text(cmake.read_text()+'''
option(CHOL_INSTRUCTION_POINTER "Reference current decoded instruction without copying" OFF)
if(CHOL_INSTRUCTION_POINTER)
  target_compile_definitions(cholesky_core PRIVATE CHOL_INSTRUCTION_POINTER=1)
endif()
''')
    (BASE/'instruction-pointer-provenance.json').write_text(json.dumps({'base_sha256':before,
        'candidate_sha256':{str(p):sha(p) for p in [src,cmake]},'preparer_sha256':sha(Path(__file__)),
        'scope':'replace current-instruction value by reference into immutable decoded vector; no default change'},indent=2))
    print('Prepared instruction-pointer candidate')


if __name__=='__main__':main()
