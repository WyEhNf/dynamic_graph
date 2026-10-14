"""Static preparation during the peer performance window.

R45 baseline; only affine seed construction becomes dependency-ready.
R46 threshold negative stays isolated. Same seed-count and16M search cap.
"""
from pathlib import Path
import hashlib
p=Path('research/batch47');p.mkdir(exist_ok=True)
old='''    std::vector<int> indices{start*k/6};std::vector<unsigned char> used(k);used[indices[0]]=1;
    while(static_cast<int>(indices.size())<k) {
      int best=-1;I best_score=-1;
      for(int q=0;q<k;++q)if(!used[q]) {'''
new='''    // Select on the real interface partial order. Unconstrained nearest
    // neighbors followed by Kahn normalization can erase producer locality.
    std::vector<int> degree(k),ready;
    for(int q=0;q<k;++q){degree[q]=static_cast<int>(s.predecessors[q].size());if(!degree[q])ready.push_back(q);}
    int first=ready[static_cast<size_t>(start)*ready.size()/6];
    std::vector<int> indices{first};std::vector<unsigned char> used(k);used[first]=1;
    for(int q:s.successors[first])--degree[q];
    while(static_cast<int>(indices.size())<k) {
      int best=-1;I best_score=-1;
      for(int q=0;q<k;++q)if(!used[q] && !degree[q]) {'''
old_tail='''      used[best]=1;indices.push_back(best);
    }
    std::vector<int> perm;for(int q:indices)perm.push_back(s.targets[q]);add(perm);'''
new_tail='''      used[best]=1;indices.push_back(best);for(int q:s.successors[best])--degree[q];
    }
    std::vector<int> perm;for(int q:indices)perm.push_back(s.targets[q]);add(perm);'''
for file in ['solution.cpp','projection.cpp.inc']:
    s=Path('research/batch45',file).read_text(encoding='utf-8');assert s.count(old)==1 and s.count(old_tail)==1
    (p/file).write_text(s.replace(old,new,1).replace(old_tail,new_tail,1),encoding='utf-8')
for file in ['diagnostic.cpp','test_projection.cpp']:(p/file).write_bytes(Path('research/batch45',file).read_bytes())
test=(p/'test_projection.cpp').read_text(encoding='utf-8')
test=test.replace('int count=0;', 'int count=0,search_count=0;std::ofstream search_output("reports/projection-search-orders-batch47.json");search_output<<"{\\\"cases\\\":[";')
test=test.replace('++count;\n  }','''++count;
    auto searched=projection_memory_search(h,g,100000);
    if(!searched.order.empty()) {
      if(!serial_evaluate(h,g,searched.order).valid){std::cerr<<"Invalid bounded search order\\n";return 1;}
      if(search_count++)search_output<<',';
      search_output<<"{\\\"name\\\":"<<local_json::quote(c.at("name").text())<<",\\\"order\\\":[";
      for(size_t q=0;q<searched.order.size();++q){if(q)search_output<<',';search_output<<g.v[searched.order[q]].id;}
      search_output<<"]}";
    }
  }''')
test=test.replace('  std::cout<<count', '  search_output<<"]}";std::cout<<search_count<<" bounded-search orders saved; ";\n  std::cout<<count')
(p/'test_projection.cpp').write_text(test,encoding='utf-8')
print(hashlib.sha256((p/'solution.cpp').read_bytes()).hexdigest())
