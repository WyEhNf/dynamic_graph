"""Isolated decoded layout experiment; wire Metadata remains untouched."""
import hashlib
import json
from pathlib import Path

BASE=Path('G:/Hackathon-stage2-artifacts/project19/20261013-bounded-stack')


def main():
    header=BASE/'workspace/include/cholesky/prepared_vm.hpp'
    decode=BASE/'workspace/src/prepared_vm.cpp';cmake=BASE/'workspace/CMakeLists.txt'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths=[header,decode,cmake];before={str(p):sha(p) for p in paths}
    for p in paths:(BASE/('precompact-'+p.name)).write_bytes(p.read_bytes())
    text=header.read_text();needle='  Opcode opcode;\n  double argument;\n  std::size_t index=0;\n  bool valid_index=false;'
    assert text.count(needle)==1
    text=text.replace(needle,'''  Opcode opcode;
#ifdef CHOL_COMPACT_DECODED
  bool valid_index=false;
#endif
  double argument;
  std::size_t index=0;
#ifndef CHOL_COMPACT_DECODED
  bool valid_index=false;
#endif''');header.write_text(text)
    text=decode.read_text();needle='    DecodedInstruction instruction{source.opcode,source.argument};'
    assert text.count(needle)==1
    text=text.replace(needle,'    DecodedInstruction instruction{};instruction.opcode=source.opcode;instruction.argument=source.argument;')
    decode.write_text(text)
    cmake.write_text(cmake.read_text()+'''
option(CHOL_COMPACT_DECODED "Place decoded validity bit in existing opcode padding" OFF)
if(CHOL_COMPACT_DECODED)
  target_compile_definitions(cholesky_core PUBLIC CHOL_COMPACT_DECODED=1)
endif()
''')
    (BASE/'compact-decoded-provenance.json').write_text(json.dumps({'base_sha256':before,
        'candidate_sha256':{str(p):sha(p) for p in paths},'preparer_sha256':sha(Path(__file__)),
        'scope':'layout-only runtime decoded records; compare same source OFF/ON; wire Metadata unchanged'},indent=2))
    print('Prepared compact decoded layout candidate')


if __name__=='__main__':main()
