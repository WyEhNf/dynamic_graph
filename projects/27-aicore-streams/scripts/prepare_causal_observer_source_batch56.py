"""Authorized SOURCE ONLY observer/driver/plan materialization, no subprocesses."""
from pathlib import Path
import hashlib,json,re,sys
P=Path('research/batch56');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
original=(P/'solution.cpp').read_bytes();assert sha(P/'solution.cpp')=='3a4f184de2759fdcd1cbfd899c5f8029e2f7f2691743ec214a895123db19c21a'
assert sha(P/'negative-checkpoint.json')=='ac02b349b312db47d83693aa8eb1da3d6359e43ffbd1750d41d4a2bdafaffead'
source=original.decode('utf-8');masked=re.sub(r'//[^\r\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m.group()),source,flags=re.S)
mods=[];inventory=[];labels=[];block_id=0
def stage(label):
    assert len(labels)<256;labels.append(label);return len(labels)-1
def observation(code,func,expression):
    if func=='causal_deferral_pair':return f'r56_observer.record({code},work,limit,r.producer<0?-1:g.v[r.producer].id,r.target<0?-1:g.v[r.target].id,(r.exhausted?2u:0u)|(r.complete?4u:0u),0);'
    if func in ('release_cut_probe','release_cut_probe_guarded'):
        target='g.v[target].id' if func.endswith('_guarded') else '-1'
        return f'r56_observer.record({code},work,limit,g.v[producer].id,{target},(r.exhausted?2u:0u)|(r.valid?1u:0u),r.order.size(),static_cast<uint64_t>(r.peak),0,false);'
    if func=='causal_deferral_restart':
        obj='retry' if expression=='retry' else 'answer'
        return f'r56_observer.record({code},work,limit,-1,-1,({obj}.exhausted?2u:0u),{obj}.order.size(),{obj}.best_peak.lo,{obj}.best_peak.hi);'
    if func=='projection_memory_search':
        obj='cut' if expression=='cut' else 'original'
        return f'r56_observer.record({code},{obj}.work,work_limit,-1,-1,({obj}.exhausted?2u:0u),{obj}.order.size(),{obj}.best_peak.lo,{obj}.best_peak.hi);'
    p,t=('-1','-1') if func=='release_cut_order' else ('g.v[delayed].id','g.v[target].id')
    return f'r56_observer.record({code},r.work,limit,{p},{t},(r.exhausted?2u:0u),r.order.size(),r.best_peak.lo,r.best_peak.hi);'
def insertion(pos,code,label):mods.append((pos,pos,code,''));inventory.append(dict(kind='additional_stage',label=label,original_line=source.count('\n',0,pos)+1,position=pos))
funcs=['causal_deferral_pair','release_cut_probe_guarded','release_cut_order_guarded','causal_deferral_restart','release_cut_probe','release_cut_order','projection_memory_search']
for func in funcs:
    m=re.search(r'(?m)^(?:CausalDeferralPair|ReleaseCut|ShallowResult) '+func+r'\(',source);assert m
    start=m.start();end=source.index('\n}',start)+2;body=source[start:end];mbody=masked[start:end]
    guard_init=body.find('I live=0,peak=0;std::vector<int> prefix;')
    for num,r in enumerate(re.finditer(r'\breturn\s+([^;\r\n]+);',mbody)):
        a=start+r.start();b=start+r.end();expression=source[a:b][len('return'):].strip()[:-1].strip();line=source.count('\n',0,a)+1
        context=source[source.rfind('\n',0,a)+1:source.find('\n',a)].strip()
        eligible=expression in ('r','answer','retry','cut','original','false') or expression.startswith('causal_deferral_restart(')
        row=dict(function=func,ordinal=num,original_line=line,original_expression=expression,original_context=context,observed=eligible,classification='original early/result return' if eligible else 'successful lambda/comparator return unchanged; not a function early failure')
        if eligible:
            label=f'{func}:return-{num}:line-{line}';code=stage(label);row.update(stage_id=code,label=label)
            if expression.startswith('causal_deferral_restart('):
                hook=observation(code,func,'r')+f'r56_observer.capture({code},g,done,users,degree,prefix,held,live);'
                row['classification']='ACTUAL original single<0 no-fit dispatch with complete physical prefix'
            else:
                hook=observation(code,func,expression)
                if func=='release_cut_order_guarded' and expression=='r' and a-start>guard_init and guard_init>=0:
                    hook+=f'r56_observer.capture({code},g,done,users,degree,r.order.empty()?prefix:r.order,r56_empty_ints,live,nullptr,false);'
                    row['snapshot']='original guarded whole return physical arrays; held not provided, derive from done/users/originalgraph'
            # Wrapper braces are wholly inside removable observation markers.
            mods.append((a,b,'{'+hook+' ', '}'))
        inventory.append(row)
    if func=='causal_deferral_restart':
        for needle,label,hook_template in [
            ('  if(!charge(3))return answer;','restart-before-entry-charge','r56_observer.record(CODE,work,limit,-1,-1,0,0);'),
            ('  if(!charge(2))return answer;','restart-detector-return-before-status-charge','r56_observer.record(CODE,work,limit,pair.producer<0?-1:g.v[pair.producer].id,pair.target<0?-1:g.v[pair.target].id,(pair.exhausted?2u:0u)|(pair.complete?4u:0u),0);'),
            ('  I remaining=limit-work;','restart-status-dispatch-paid-before-guard','r56_observer.record(CODE,work,limit,g.v[pair.producer].id,g.v[pair.target].id,8,0);'),
            ('  if(!charge(4))return answer;','restart-guard-return-before-merge-charge','r56_observer.record(CODE,work,limit,g.v[pair.producer].id,g.v[pair.target].id,(retry.exhausted?2u:0u),retry.order.size(),retry.best_peak.lo,retry.best_peak.hi);')]:
            pos=source.index(needle,start,end);code=stage(label);insertion(pos,hook_template.replace('CODE',str(code)),label)
    if func=='projection_memory_search':
        pos=source.index('  auto original=projection_memory_search_r48',start,end);label='wrapper-cut-return-before-projection';code=stage(label)
        insertion(pos,f'r56_observer.record({code},cut.work,work_limit,-1,-1,(cut.exhausted?2u:0u),cut.order.size(),cut.best_peak.lo,cut.best_peak.hi);',label)
def marker(content):
    global block_id
    block_id+=1;return f'/*R56_OBS_BLOCK_{block_id}_BEGIN*/'+content+f'/*R56_OBS_BLOCK_{block_id}_END*/'
pos=source.index('namespace aicore_detail');mods.append((pos,pos,'#include <array>\n',''))
pos=source.index('struct CausalDeferralPair');mods.append((pos,pos,(P/'observer-support.cpp.inc').read_text()+'\n',''))
out=source
for a,b,before,after in sorted(mods,key=lambda x:(x[0],x[1]),reverse=True):
    out=out[:a]+marker(before)+source[a:b]+(marker(after) if after else '')+out[b:]
stripped=re.sub(r'/\*R56_OBS_BLOCK_(\d+)_BEGIN\*/.*?/\*R56_OBS_BLOCK_\1_END\*/','',out,flags=re.S)
assert stripped.encode('utf-8')==original
target=P/'observer-solution.cpp';assert not target.exists();target.write_bytes(out.encode('utf-8'))
driver=(P/'selected12-driver.cpp').read_text()
driver=re.sub(r'#ifdef R52_OBSERVER\s*#include "observer-solution.cpp"\s*#else\s*#include "solution.cpp"\s*#endif','#include "observer-solution.cpp"',driver)
driver=re.sub(r'#ifdef R52_OBSERVER\s*aicore_detail::observer.reset\(\);\s*#endif','aicore_detail::r56_observer.reset();',driver)
driver=re.sub(r'#ifdef R52_OBSERVER\s*out<<",\\"helper_observer\\":"<<aicore_detail::observer_json\(\);\s*aicore_detail::observer.reset\(\);\s*#endif','out<<",\\"helper_observer\\":"<<r56_observer_json();\n    aicore_detail::r56_observer.reset();',driver)
driver=re.sub(r'#ifdef R52_OBSERVER\s*out<<",\\"whole_observer\\":"<<aicore_detail::observer_json\(\);\s*#endif','out<<",\\"whole_observer\\":"<<r56_observer_json();',driver)
assert 'R52_OBSERVER' not in driver and 'aicore_detail::observer' not in driver
definition='static const std::array<const char*,'+str(len(labels))+'> r56_stage_labels={'+','.join(json.dumps(x) for x in labels)+'};\n'+(P/'observer-serializer.cpp.inc').read_text()+'\n'
driver=driver.replace('int main(int argc,char** argv)',definition+'int main(int argc,char** argv)')
target=P/'observer-driver.cpp';assert not target.exists();target.write_text(driver,encoding='utf-8')
inventory_path=P/'observer-return-inventory.json';assert not inventory_path.exists();inventory_path.write_text(json.dumps(dict(status='SOURCE_ONLY_ALL_SEVEN_TARGET_FUNCTION_RETURNS_INVENTORIED',source_sha256=sha(P/'solution.cpp'),observer_source_sha256=sha(P/'observer-solution.cpp'),stage_labels=labels,rows=inventory,marked_blocks=block_id,source_roundtrip_bytes_identical=True,guarded_probe_metadata='count-only every original return, no fullstate; physical fullstates originalouter-no-fit then firstguardedwhole return',coverage='These seven functions only; not every scheduler function. Successful/comparator returns explicitly unchanged. Actual runtime stage coverage still untested.'),indent=2)+'\n',encoding='utf-8')
owned='G:/Hackathon-project27-owned/batch56-observer-'+sha(P/'observer-solution.cpp')[:8];assert not Path(owned).exists()
plan=json.loads((P/'selected12-resource-plan.json').read_text());plan.update(status='SOURCE_ONLY_OBSERVER_PLAN_NOT_EXECUTED_ROOT_REVIEW_REQUIRED',owned_root=owned,exe_path=owned+'/bin/observer-gcc.exe',exe_sha256=None,source_path=str(P/'observer-solution.cpp'),source_sha256=sha(P/'observer-solution.cpp'),expected_saved_raw_path='G:/Hackathon-project27-owned/batch56-selected12-79cecf/outputs/selected12.json',expected_saved_raw_sha256=sha('G:/Hackathon-project27-owned/batch56-selected12-79cecf/outputs/selected12.json'),process_environment_overrides={k:owned+'/process-temp' for k in ('TEMP','TMP','TMPDIR')},scope='Observer source-only now; future authorized GCC O2 observer compile+once original12 and strict savedR56 fieldcomparison; no baseline rerun/control/63/full/perf/default/TeX',ABI='problem.h unchanged; standalone production solution unchanged. Observer global/debug fields internal namespace only. One benchmark main macro-renamed; observerdriver own main. stdlib fixedstorage only.',file_stdio='Algorithm emits no IO; observer serializers execute after helper/whole calls only. Future compiler/runtime stdout/stderr and JSON file-backed on owned G. Fresh64-byte GlobalMemoryStatusEx RAM1GiB/G1GiB/F64MiB before everychild, status/raw firstfail/no retry.',commands=[dict(label='build-observer-gcc',argv=['E:/mingw64/bin/g++.exe','-O2','-std=c++17','-Iinclude',str(P/'observer-driver.cpp'),'src/simulator.cpp','-o',owned+'/bin/observer-gcc.exe']),dict(label='observer-original12-once',argv=[owned+'/bin/observer-gcc.exe',plan['input_path'],owned+'/outputs/observer12.json']),dict(label='compare-observer-exact-fields',argv=[sys.executable,'scripts/verify_causal_observer_roundtrip_batch56.py','--actual',owned+'/outputs/observer12.json'])])
plan_path=P/'observer-resource-plan.json';assert not plan_path.exists();plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
roundtrip=dict(status='SOURCE_ONLY_MARKER_REMOVAL_BYTE_EXACT',original_sha256=sha(P/'solution.cpp'),observer_sha256=sha(P/'observer-solution.cpp'),stripped_sha256=hashlib.sha256(stripped.encode()).hexdigest(),original_bytes=len(original),marked_blocks=block_id,target_functions=len(funcs),stage_count=len(labels),metadata_per_scope_limit=16,state_per_scope_limit=2,array_limit=4096,implemented_not_compiled=True,solver_not_executed=True)
target=P/'observer-source-roundtrip.json';assert not target.exists();target.write_text(json.dumps(roundtrip,indent=2)+'\n',encoding='utf-8');print(json.dumps(roundtrip,indent=2))
