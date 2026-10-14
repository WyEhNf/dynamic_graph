from pathlib import Path
base=Path('research/batch42/solution.cpp').read_text(encoding='utf-8');old=Path('research/batch41/solution.cpp').read_text(encoding='utf-8')
s=base
start=s.index('std::vector<int> strict_fork_join_order(');end=s.index('\nstruct SerialFrontierResult',start)
start_old=old.index('std::vector<int> strict_fork_join_order(');end_old=old.index('\nstruct SerialFrontierResult',start_old)
s=s[:start]+old[start_old:end_old]+s[end:]
a='''    std::set<std::vector<int>> seen_macro;
    if(!impossible)for(const auto& closure:closures) {
      std::vector<int> pending;for(int i:closure)if(!done[i])pending.push_back(i);
      if(pending.size()<2 || !seen_macro.insert(pending).second)continue;'''
b='''    std::set<std::vector<unsigned long long>> seen_macro;
    if(!impossible)for(const auto& closure:closures) {
      std::vector<unsigned long long> pending(words);size_t pending_count=0;
      for(int i:closure)if(!done[i]){pending[i/64]|=1ull<<(i%64);++pending_count;}
      if(pending_count<2 || !seen_macro.insert(pending).second)continue;'''
assert a in s;s=s.replace(a,b)
a='      if(fit && order.size()>begin+1)macros.push_back({std::vector<int>(order.begin()+begin,order.end()),live,peak});'
x=old.index('      if(fit && order.size()>begin+1) {');y=old.index('\n      while(order.size()>begin)',x)
assert a in s;s=s.replace(a,old[x:y])
p=Path('research/batch43');p.mkdir(exist_ok=True);(p/'solution.cpp').write_text(s,encoding='utf-8')
s=Path('research/batch41/streaming_equivalence.cpp').read_text(encoding='utf-8').replace('../batch39/solution.cpp','../batch42/solution.cpp')
(p/'streaming_equivalence.cpp').write_text(s,encoding='utf-8')
s=Path('research/batch42/test_serial_frontier.cpp').read_text(encoding='utf-8');(p/'test_serial_frontier.cpp').write_text(s,encoding='utf-8')
print('R43 resource-only rebase on exact R42, node support/search budgets unchanged')
