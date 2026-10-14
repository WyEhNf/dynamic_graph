"""File materialization only. No compilation, solver, reference evaluation."""
from pathlib import Path
import hashlib,json
p=Path('research/batch56');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
base=Path('research/batch51/solution.cpp')
assert sha(base)=='8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b'
text=base.read_text(encoding='utf-8');old=Path('research/batch51/release-cut.cpp.inc').read_text(encoding='utf-8');assert text.count(old)==1
head,rest=old.split('ReleaseCut release_cut_probe(',1)
probe,outer=('ReleaseCut release_cut_probe('+rest).split('ShallowResult release_cut_order(',1)
outer='ShallowResult release_cut_order('+outer
guardprobe=probe.replace('ReleaseCut release_cut_probe(','ReleaseCut release_cut_probe_guarded(',1)
guardprobe=guardprobe.replace('I live,I& work,I limit) {','I live,I& work,I limit,int delayed,int target) {',1)
needle='      if(done[i] || degree[i])continue;'
assert guardprobe.count(needle)==1
guardprobe=guardprobe.replace(needle,needle+'\n      if(!charge(2))return r;if(i==delayed && !done[target])continue;',1)
guardouter=outer.replace('ShallowResult release_cut_order(const HardwareInfo& h,const Graph& g,I limit)',
                        'ShallowResult release_cut_order_guarded(const HardwareInfo& h,const Graph& g,I limit,int delayed,int target)',1)
guardouter=guardouter.replace('    if(done[i] || degree[i] || !memory_fits(',
                            '    if(!charge(2))return false;if(i==delayed && !done[target])return false;\n    if(done[i] || degree[i] || !memory_fits(',1)
needle='      if(degree[i] || !memory_fits('
assert guardouter.count(needle)==1
guardouter=guardouter.replace(needle,'      if(!charge(2))return r;if(i==delayed && !done[target])continue;\n'+needle,1)
guardouter=guardouter.replace('release_cut_probe(h,g,p,done,users,degree,live,r.work,limit)',
                            'release_cut_probe_guarded(h,g,p,done,users,degree,live,r.work,limit,delayed,target)',1)
restart='''// Retry at most once. This function is never called by the guarded copy.
ShallowResult causal_deferral_restart(const HardwareInfo& h,const Graph& g,
 const std::vector<unsigned char>& done,const std::vector<int>& users,
 const std::vector<int>& prefix,const std::vector<int>& held,I& work,I limit,int evaluations) {
  ShallowResult answer;answer.evaluations=evaluations;
  auto charge=[&](I amount){if(cut_charge(work,limit,amount))return true;answer.order.clear();answer.exhausted=true;answer.work=work;return false;};
  if(!charge(3))return answer;
  auto pair=causal_deferral_pair(h,g,done,users,prefix,held,work,limit);
  if(!charge(2))return answer;
  if(!pair.complete || pair.producer<0){answer.exhausted=pair.exhausted;answer.work=work;return answer;}
  if(!charge(2))return answer;
  I remaining=limit-work;
  auto retry=release_cut_order_guarded(h,g,remaining,pair.producer,pair.target);
  work+=retry.work; // retry.work<=remaining, no signed overflow, same2M account.
  if(!charge(4))return answer; // Merge/result status and evaluations before use.
  retry.evaluations+=evaluations;retry.work=work;return retry;
}
'''
helper=(p/'causal-detector.cpp.inc').read_text(encoding='utf-8')+'\n'+guardprobe+'\n'+guardouter+'\n'+restart
(p/'causal.cpp.inc').write_text(helper,encoding='utf-8',newline='\n')
oldfallback='    else {if(single<0 || !apply(single))return r;}'
assert outer.count(oldfallback)==1
newfallback='''    else {
      if(single<0)return causal_deferral_restart(h,g,done,users,prefix,held,r.work,limit,r.evaluations);
      if(!apply(single))return r;
    }'''
new=head+helper+'\n'+probe+outer.replace(oldfallback,newfallback,1)
(p/'release-cut.cpp.inc').write_text(new,encoding='utf-8',newline='\n')
(p/'solution.cpp').write_text(text.replace(old,new,1),encoding='utf-8',newline='\n')
doc=dict(status='SOURCE_ONLY_NOT_COMPILED_OR_EXECUTED',base_sha256=sha(base),source_sha256=sha(p/'solution.cpp'),
         fragment_sha256=sha(p/'causal.cpp.inc'),expanded_release_cut_sha256=sha(p/'release-cut.cpp.inc'),
         changes=['add paid pair detector and separately copied guarded R51 probe/order',
                  'sole original outer no-progress single<0 return dispatches one retry'],
         original_success_code_unchanged=True,default_unchanged=True,no_R53_R55_or_witness_features=True)
(p/'source-provenance.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(json.dumps(doc))
