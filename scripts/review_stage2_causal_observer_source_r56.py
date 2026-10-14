"""Root exact source restoration, observation isolation and run plan review."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'projects/27-aicore-streams';D=P/'research/batch56'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    m=read(D/'observer-source-plan-freeze.json');i=read(D/'observer-return-inventory.json');plan=read(D/'observer-resource-plan.json')
    assert sha(D/'observer-source-plan-freeze.json')=='113f34a8e4b0480c8273793658f95b8e677a91711c1b4218efeeab993f0f6439'
    for item in m['files']:
        p=Path(item['path']);p=p if p.is_absolute() else P/p;assert sha(p)==item['sha256'] and p.stat().st_size==item['bytes'],str(p)
    original=(D/'solution.cpp').read_bytes();source=(D/'observer-solution.cpp').read_text(encoding='utf-8')
    pattern=r'/\*R56_OBS_BLOCK_(\d+)_BEGIN\*/(.*?)/\*R56_OBS_BLOCK_\1_END\*/';blocks=re.findall(pattern,source,re.S)
    assert len(blocks)==len({n for n,_ in blocks})==m['marked_blocks']==i['marked_blocks']==211
    stripped=re.sub(pattern,'',source,flags=re.S);assert stripped.encode()==original and sha(D/'solution.cpp')=='3a4f184de2759fdcd1cbfd899c5f8029e2f7f2691743ec214a895123db19c21a'
    assert len(i['rows'])==119 and len(i['stage_labels'])==107 and len(set(i['stage_labels']))==107
    oldlines=original.decode().splitlines()
    for row in i['rows']:
        if row.get('kind')=='additional_stage':
            assert row['label'] in i['stage_labels'] and original[:row['position']].count(b'\n')+1==row['original_line'];continue
        assert row['original_context'] in oldlines[row['original_line']-1],row
        assert re.search(r'\breturn\s+'+re.escape(row['original_expression'])+r'\s*;',oldlines[row['original_line']-1])
    added='\n'.join(b for _,b in blocks)
    assert 'std::array<R56ObservationMeta,16>' in added and 'std::array<R56ObservationState,2>' in added and 'std::array<uint64_t,256>' in added
    assert 'std::array<int,4096>' in added and 'std::array<unsigned char,4096>' in added
    # Entire observer implementation read by root. Other blocks only wrap an
    # unchanged return, record scalar actual values, or capture const arrays.
    for number,text in blocks:
        if int(number) not in [210,211]:
            assert not re.search(r'\b(?:throw|new|malloc|printf|cout|cerr|ofstream)\b',text)
            assert not re.search(r'\b(?:work|limit|done|users|degree|prefix|held|r|retry|cut|original)\s*(?:\+\+|--|\+=|-=|=(?!=))',text)
    driver=(D/'observer-driver.cpp').read_text();assert driver.count('aicore_detail::r56_observer.reset();')==2
    assert driver.index('projection_memory_search(h,g)')<driver.index('helper_observer') and driver.index('ScheduleCvGraph(h,nodes')<driver.index('whole_observer')
    assert plan['commands'][0]['argv'][1:3]==['-O2','-std=c++17'] and len(plan['commands'])==3
    assert plan['input_sha256']==sha(P/plan['input_path'])=='7e6b7f9b1bf267a28244c1ec4eb47146d67fe54f2a582b04a665db7633716e79'
    assert sha(plan['expected_saved_raw_path'])==plan['expected_saved_raw_sha256']=='2df75ec8cf22c18b0b64f8499800589d09a6694e3dbb7c987172397c4495b55f'
    assert plan['minimum_available_RAM_bytes']==plan['minimum_G_free_bytes']==1073741824 and plan['minimum_F_free_small_state_bytes']==67108864
    assert Path(plan['owned_root']).drive.upper()=='G:' and not Path(plan['owned_root']).exists() and not (D/'observer-execution-status.json').exists()
    result=dict(passed=True,source_only=True,source_plan_sha256=sha(D/'observer-source-plan-freeze.json'),frozen_files=36,marker_blocks=211,byte_exact_original_source=True,return_inventory_rows=119,stage_ids=107,bounds=dict(metadata=16,states=2,array_elements=4096,stage_counters=256),review=['Only fixed global observer storage changes; no algorithm input, fee, comparator, calls, budgets or default changes','Source returns wrapped and directly counted; successful lambda/comparator returns explicitly excluded; cut/r48 exhausted separate','Helper/whole reset before each actual call; serializers after execution; sampling drops and observer errors explicit','Driver strictly compares every nonobserver field to saved original12; every original complete plan needs root replay; observation timing not performance'],authorized_next='One isolated observer compile+original12+strict equality after current19 cost window is terminal; no baseline/control/63/full rerun. Full trace coverage is not claimed with16/2 sampling.')
    (ROOT/'outputs/stage2-root-causal-observer-source-r56.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
