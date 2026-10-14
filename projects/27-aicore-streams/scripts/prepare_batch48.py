"""Static R45-based group-move candidate. Run only after validation boundary."""
from pathlib import Path
import hashlib
p=Path('research/batch48');p.mkdir(exist_ok=True)
helper='''std::vector<std::pair<std::vector<int>,I>> direct_consumer_groups(const Graph& g,const WorkspaceProjection& s,I& work,I limit,bool& exhausted) {
  std::map<std::vector<int>,I> grouped;
  for(int p=0;p<g.n;++p)if(s.position[p]<0 && g.v[p].output_memory && g.out[p].size()>=2 && g.out[p].size()<=4) {
    std::vector<int> members;bool all=true;
    for(int c:g.out[p]){if(++work>limit){exhausted=true;return {};}if(s.position[c]<0){all=false;break;}members.push_back(c);}
    if(!all)continue;std::sort(members.begin(),members.end());
    grouped[members]=positive_add(grouped[members],g.v[p].output_memory);
  }
  std::vector<std::pair<std::vector<int>,I>> groups(grouped.begin(),grouped.end());
  std::stable_sort(groups.begin(),groups.end(),[](const auto& a,const auto& b){return a.second>b.second;});return groups;
}
std::vector<int> move_consumer_group(const std::vector<int>& permutation,const std::vector<int>& group,int pivot) {
  std::vector<int> block,remaining;int removed_before=0;
  for(size_t q=0;q<permutation.size();++q) {
    int v=permutation[q];
    if(std::find(group.begin(),group.end(),v)!=group.end()){block.push_back(v);if(static_cast<int>(q)<pivot)++removed_before;}
    else remaining.push_back(v);
  }
  int destination=std::max(0,std::min(static_cast<int>(remaining.size()),pivot-removed_before));
  remaining.insert(remaining.begin()+destination,block.begin(),block.end());return remaining;
}
'''
group_setup='''  // Original direct-consumer sets only; a group proposes an ordering
  // move, never a fused operation, transformed edge or early release.
  auto groups=direct_consumer_groups(g,s,result.work,work_limit,result.exhausted);if(result.exhausted)return result;
'''
escape='''      // Evaluate block insertions only at a single-node local minimum.
      // Overlapping groups are separate candidates. Normalization enforces
      // all original interface dependencies; closure profiles charge W+O.
      if(!improved && result.work+s.unit<=local_limit) {
        std::vector<int> position(g.n,-1);for(int q=0;q<k;++q)position[perm[q]]=q;
        int tried=0;std::set<std::vector<int>> seen_permutations;
        for(const auto& group:groups) {
          int first=k,last=-1;for(int c:group.first){first=std::min(first,position[c]);last=std::max(last,position[c]);}
          if(first==last || !(first<=critical && critical<last))continue;
          if(++tried>24)break;
          for(int pivot:{critical,critical+1}) {
            if(result.work+s.unit>local_limit)break;
            auto candidate=move_consumer_group(perm,group.first,pivot);
            if(candidate==perm || !seen_permutations.insert(candidate).second)continue;
            auto p=evaluate(candidate);if(p<best){best=std::move(p);improved=true;}
            if(feasible(best)){result.order=std::move(best.order);return result;}
          }
        }
      }
'''
for file in ['solution.cpp','projection.cpp.inc']:
    s=Path('research/batch45',file).read_text(encoding='utf-8')
    if file=='solution.cpp':s=s.replace('#include <stdexcept>','#include <stdexcept>\n#include <map>',1)
    marker='ShallowResult projection_memory_search(';assert s.count(marker)==1;s=s.replace(marker,helper+marker,1)
    marker='  auto feasible=[](const ProjectionProfile& p)';assert s.count(marker)==1;s=s.replace(marker,group_setup+marker,1)
    marker='      if(!improved || result.work+s.unit>local_limit)break;';assert s.count(marker)==1;s=s.replace(marker,escape+marker,1)
    (p/file).write_text(s,encoding='utf-8')
for file in ['diagnostic.cpp','test_projection.cpp']:(p/file).write_bytes(Path('research/batch45',file).read_bytes())
print(hashlib.sha256((p/'solution.cpp').read_bytes()).hexdigest())
