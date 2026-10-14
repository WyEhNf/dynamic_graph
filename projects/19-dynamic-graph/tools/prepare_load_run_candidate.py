"""Prepare an isolated <=4 LOAD run candidate; never change the default VM.

The inherited pair metric now counts removed dispatches, not run count.
Every original NEXT/step/error boundary is still executed in sequence.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

SOURCE = Path('G:/Hackathon-stage2-artifacts/project19/load-pair/workspace')
DEST = Path('G:/Hackathon-stage2-artifacts/project19/load-run4/workspace')


def main():
    if DEST.exists():
        if '--resume-preparation' not in sys.argv or (DEST.parent/'source-provenance.json').exists(): raise FileExistsError(DEST)
        if (DEST/'src/load_pair_vm.cpp').read_bytes() != (SOURCE/'src/load_pair_vm.cpp').read_bytes(): raise AssertionError('partial source differs')
    else: shutil.copytree(SOURCE, DEST)
    path = DEST / 'src/load_pair_vm.cpp'
    text = path.read_text(encoding='utf-8')
    old = '''      result.starts[pc]=1;++result.pairs;pc+=2; // Greedy disjoint pairs.'''
    new = '''      unsigned length=2;
      while(length<4&&pc+length<decoded.size()&&decoded[pc+length].opcode==Opcode::Load&&!entries[pc+length])++length;
      result.starts[pc]=static_cast<unsigned char>(length);
      result.pairs+=length-1;pc+=length; // Disjoint runs; metric = removed dispatches.'''
    if text.count(old) != 1: raise AssertionError('discovery source changed')
    text = text.replace(old, new)
    start = text.index('  if(load_pairs.valid&&load_pairs.starts[pc-1]) {')
    end = text.index('\n}NEXT();', start)
    text = text[:start] + '''  const unsigned run_length=load_pairs.valid?load_pairs.starts[pc-1]:0;
  for(unsigned extra=1;extra<run_length;++extra) {
    // Preserve each original LOAD's NEXT boundary, PC and step limit.
    if(stack.size()>4096)throw std::runtime_error("bytecode stack overflow");
    last_pc=pc;
    if(++steps>options.vm_step_limit)throw std::runtime_error("VM instruction limit exceeded");
    instruction=decoded[pc];++pc;
    const auto next_slot=immediate("slot");
    if(!initialized[next_slot])throw std::runtime_error("read of uninitialized scalar");
    stack.push_back(slots[next_slot]);++executed_pairs;
  }''' + text[end:]
    path.write_text(text, encoding='utf-8')
    tests = DEST / 'tests/load_pair_vm_tests.cpp'
    text = tests.read_text(encoding='utf-8').replace(
        'vm_fusion_pairs_discovered==2&&result.metric.vm_fusion_pairs_executed==2',
        'vm_fusion_pairs_discovered==3&&result.metric.vm_fusion_pairs_executed==3')
    needle = '  ++extra_cases;\n  for(I bad:'
    addition = '''  ++extra_cases;
  for(std::uint64_t limit=0;limit<=chain.program.size()+1;++limit)(void)compare(chain,limit);
  // Invalid third/fourth operands, uninitialized fourth and interior side entries.
  for(unsigned position=5;position<=7;++position) {
    auto invalid=chain;invalid.program[position].argument=99;
    group("interior-invalid-load",invalid,"invalid slot",{});
  }
  auto uninit=chain;uninit.program[7].argument=0;
  uninit.program.insert(uninit.program.begin(),{O::Uninit,0});
  group("fourth-uninitialized",uninit,"read of uninitialized scalar",{});
  for(unsigned destination=5;destination<=7;++destination) {
    auto entry=chain;entry.program.insert(entry.program.begin()+4,{O::Jump,double(destination+1)});
    // Add a jump only as a classification edge, bypass it during execution.
    entry.program[4]={O::Const,0};entry.program.push_back({O::Jump,double(destination+1)});
    (void)compare(entry,1000000000);
    for(std::uint64_t limit=0;limit<=entry.program.size()+1;++limit)(void)compare(entry,limit);
  }
  for(I bad:''' 
    if text.count(needle) != 1: raise AssertionError('test insertion changed')
    text = text.replace(needle, addition).replace('original_groups==15','original_groups==19')
    tests.write_text(text, encoding='utf-8')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {'variant':'entry-safe LOAD runs, maximum 4', 'default_changed':False,
        'source':str(SOURCE), 'destination':str(DEST),
        'metric_semantics':'vm_fusion_pairs_* = removed original dispatches',
        'parent_vm_sha256':sha(SOURCE/'src/load_pair_vm.cpp'),
        'candidate_vm_sha256':sha(path), 'tests_sha256':sha(tests),
        'preparer_sha256':sha(Path(__file__))}
    (DEST.parent/'source-provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest))


if __name__=='__main__': main()
