"""Isolated direct-target dispatch experiment after bounded-stack evidence."""
import hashlib
import json
from pathlib import Path

BASE=Path('G:/Hackathon-stage2-artifacts/project19/20261013-bounded-stack')


def main():
    src=BASE/'workspace/src/threaded_vm.cpp';cmake=BASE/'workspace/CMakeLists.txt'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={str(p):sha(p) for p in [src,cmake]}
    (BASE/'byte-threaded_vm.cpp').write_bytes(src.read_bytes())
    (BASE/'byte-CMakeLists.txt').write_bytes(cmake.read_bytes())
    text=src.read_text()
    needle='  static_assert(sizeof(targets)/sizeof(targets[0])==33);'
    assert text.count(needle)==1
    text=text.replace(needle,needle+'''
#ifdef CHOL_DIRECT_TARGETS
  std::vector<void*> direct_targets;
  direct_targets.reserve(decoded.size());
  for(const auto& item:decoded) {
    const auto code=static_cast<unsigned>(item.opcode);
    direct_targets.push_back(code<33?targets[code]:&&LInvalid);
  }
  if(options.metrics) {
    options.metrics->vm_prepare_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-prepare_start).count();
    options.metrics->vm_plan_bytes+=direct_targets.capacity()*sizeof(void*);
  }
#define JUMP_TARGET() goto *direct_targets[pc-1]
#else
#define JUMP_TARGET() do {const auto code=static_cast<unsigned>(instruction.opcode);if(code>=33)goto LInvalid;goto *targets[code];} while(false)
#endif''')
    needle='  const auto code=static_cast<unsigned>(instruction.opcode); \\\n  if(code>=33)goto LInvalid; \\\n  goto *targets[code]; \\'
    assert text.count(needle)==1
    text=text.replace(needle,'  JUMP_TARGET(); \\')
    text=text.replace('#undef DISPATCH','#undef DISPATCH\n#undef JUMP_TARGET')
    src.write_text(text)
    cmake.write_text(cmake.read_text()+'''
option(CHOL_DIRECT_TARGETS "Predecode threaded handler targets" OFF)
if(CHOL_DIRECT_TARGETS)
  target_compile_definitions(cholesky_core PRIVATE CHOL_DIRECT_TARGETS=1)
endif()
''')
    (BASE/'direct-targets-provenance.json').write_text(json.dumps({'base_sha256':before,
        'candidate_sha256':{str(p):sha(p) for p in [src,cmake]},'preparer_sha256':sha(Path(__file__)),
        'scope':'direct handler targets; costs eight extra bytes per source instruction on x64; no default change'},indent=2))
    print('Prepared direct-targets candidate')


if __name__=='__main__':main()
