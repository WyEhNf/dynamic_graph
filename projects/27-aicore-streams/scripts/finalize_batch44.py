"""Finalize an authorized recovery default after actual build/CTest evidence."""
import hashlib,json,re,shutil
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=sha('solution/solution.cpp');assert source==sha('research/batch44/solution.cpp')
ctest=Path('reports/ctest-batch44.txt').read_text(encoding='utf-8');assert '100% tests passed' in ctest and '11/11' in ctest
elapsed=float(re.search(r'Total Test time \(real\) =\s+([\d.]+)',ctest).group(1))
cost=json.loads(Path('reports/resource-cost-summary-batch44.json').read_text());functional=json.loads(Path('reports/functional-summary-batch44.json').read_text())
assert source==functional['source_sha'];assert functional['comparisons']['hard']['after_legal']==141
for family in ['hard','heldout']:
    r=cost[family];assert r['source_sha']==source and len(r['rounds'])==3
    assert all(len(x['recovered'])=={'hard':2,'heldout':4}[family] for x in r['rounds'])
# Direct cached R43 comparison is separate from the earlier historical suite
# baselines. Hash every original file so this claim can be independently read.
reg=json.loads(Path('reports/regression-batch44.json').read_text());direct=[]
for suite in reg['comparisons']:
    a=Path(f'reports/{suite}-batch43.json');b=Path(f'reports/{suite}-batch44.json');old={x['name']:x for x in json.loads(a.read_text())['cases']};new={x['name']:x for x in json.loads(b.read_text())['cases']};assert old.keys()==new.keys()
    assert all((old[k]['pass'],old[k]['T'],old[k]['peak_memory'])==(new[k]['pass'],new[k]['T'],new[k]['peak_memory']) for k in old)
    direct.append(dict(suite=suite,records=len(old),before=str(a),after=str(b),before_sha=sha(a),after_sha=sha(b)))
Path('reports/direct-normal-r43-batch44.json').write_text(json.dumps(dict(records=979,all_same=True,baseline_source_sha=sha('research/batch43/solution.cpp'),source_sha=source,suites=direct),indent=2),encoding='utf-8')
unresolved=[dict(name=x['name'],n=x['n'],error=x['error']) for x in json.loads(Path('reports/hard-functional-batch44.json').read_text())['cases'] if not x['pass']];assert len(unresolved)==61
candidate=json.loads(Path('research/batch44/candidate-provenance.json').read_text())
assert candidate['compile_inputs']['CMakeLists.txt']==sha('research/batch44/CMakeLists-measured.txt')
compile_inputs=['solution/solution.cpp','CMakeLists.txt']+[str(p).replace('\\','/') for directory in ['src','include'] for p in sorted(Path(directory).glob('*')) if p.suffix in ['.cpp','.h']]
tests=['tests/test_simulator.cpp','tests/test_models.cpp','tests/test_assignment.cpp','tests/test_serial_frontier.cpp','tests/test_numeric.cpp','tests/test_numeric_priority.cpp','tests/test_shallow.cpp']
flags=['build/CMakeFiles/solution.dir/flags.make','build/CMakeFiles/aicore_bench.dir/flags.make','build/CMakeFiles/simulator.dir/flags.make']
m=dict(status='validated_recovery_default_milestone',source_sha256=source,default_exe_sha256=sha('build/aicore_bench.exe'),measured_exe_sha256=cost['hard']['exe_sha'],measured_build_inputs=candidate['compile_inputs'],measured_CMake_snapshot='research/batch44/CMakeLists-measured.txt',compile_inputs={p:sha(p) for p in compile_inputs},test_inputs={p:sha(p) for p in tests},generation_inputs=candidate['generation_inputs'],release_flags={p:Path(p).read_text() for p in flags},independent_simulator_sha256=sha('src/simulator.cpp'),old_default_R43_source_sha=sha('research/batch43/solution.cpp'),old_default_R43_exe_sha=sha('research/batch43/default-aicore_bench.exe'),old_R43_freeze='research/batch43/provenance.json',normal_original_records=1229,normal_original_passed_according_to_expectation=1168,new_heldout_records=72,new_heldout_passed=72,total_records=1301,total_passed_according_to_expectation=1240,total_expected_infeasible=1,known_witness_unresolved=61,count_caveat='Parameter-repeat records are retained. 1240 expectation passes include one expected-infeasible rejection, not1240 feasible outputs. Bigint/profile controls separate. Original2 recoveries share one topology; new4 are heldout seeds.',hard_records=202,hard_legal=141,new_structure_records=36,new_structure_legal=36,recovery=dict(original_records=2,original_topologies=1,new_heldout_records=4,lost=0,common_243_T_peak_identical=True),unresolved=unresolved,strict_regression_records=979,strict_regression_wall_seconds=reg['elapsed_wall_seconds'],strict_regression_baseline='Historical8..22 no regression; distinct direct R43 cached979 full equality proof reports/direct-normal-r43-batch44.json',optimum_audits=144,optimal_certificates=33,ctest=f'11/11 passed: original10 plus new profile gold; {elapsed:.2f}s',ctest_report_sha=sha('reports/ctest-batch44.txt'),numeric_fixed_plan_gold=523,numeric_validation='R44 real source Clang21 UBSan fixed plans523 all matched Python bigint; newprofile2590/160 bounded validity no runtime UB diagnostics',priority_arbitrary_precision_gold=20180,priority_execution='Actual new-default GCC numeric_priority_exact_gold test reran20180; no new UBSan priority claim',profile_bigint_gold=2590,profile_search_validity=160,exchange_controls=756,exchange_caveat='Constant previously live prefix required; mixed release negative control preserved',numeric_controls=candidate['numeric_fixed_plan'],functional_source_exe=candidate['functional_source_exe'],paired_plan_sha=sha('research/batch44/paired-plan.json'),paired_cost=cost,timing_caveat='Recovery portfolio costs more on full202; per-pair CPU median+9.19%, independent-side median ratio+4.49%. Retain failure costs and raw pair ratios; not an overall speedup. 72 favorable CPU does not generalize.',old_frozen_R31_tex_sha=sha('reports/project27-research.tex'),single_file='problem.h plus standard library; .inc fully expanded, no runtime external oracle/witness/third-party dependency',support='Original R43 portfolio preserved; additional recovery only after failed original search. n<=4096/consumer<=512, charged12M profile+affinity work, seed container/sorting/generation costs not included in charged count. No infeasibility certificate on exhaustion.',default_build_evidence='reports/build-batch44.txt',LF_hash_note='Preparation normalized-string SHA was corrected; all freeze and functional metadata use actual file bytes.')
m['default_exe_path']='build/aicore_bench.exe'
m['measured_exe_path']='research/batch44/measured-release-aicore_bench.exe'
m['performance_executed_exe_path']='research/batch44/build/aicore_bench.exe'
m['functional_O2_exe_path']='research/batch44/aicore_bench.exe'
assert sha(m['measured_exe_path'])==m['measured_exe_sha256']
m['data_inputs']=dict(candidate['data_inputs'])
for p in ['data/priority-gold-batch42.txt','data/resource-cliques-batch31.json']+[f'data/{label}-batch42.json' for label in ['numeric-controls','numeric-parallel','numeric-parallel-valid','scaled-serial-controls']]:m['data_inputs'][p]=sha(p)
shutil.copyfile('build/aicore_bench.exe','research/batch44/default-aicore_bench.exe')
for p in ['reports/final-checkpoint-batch44.json','research/batch44/provenance.json']:Path(p).write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
p=Path('docs/validation.json');d=json.loads(p.read_text(encoding='utf-8'));d['latest_default_checkpoint']=m;d['shallow_recovery_batch44']=m;p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
text=f'''\n\n第44批当前默认：输入-only浅层共享producer/consumer恢复分支，仅原R43全失败后触发，不读witness/名字。原202困难139→141，2条来自同一拓扑的内存参数变体；72新种子持出68→72，4个未见种子恢复；共同243 T/peak全同、0丢失/分歧。旧1229记录1168按预期通过，加72新图共1301/1240按预期通过（含1预期不可行拒绝），仍61条有witness未解。原36结构、979直接R43逐记录全部同T/peak。\n\n多个prefix的真实输出存活逐原始DIRECT边计算，生产者W降序只在已有prefix存活恒定的组启用，变化prefix反例保留；标准库双64位诊断剖面避免超MAX后释放失真，实际计划仍由独立Event模拟器验证。2590独立Python-bigint剖面/160搜索有效性、756恒live交换/变化prefix负控制、523 UBSan数值计划通过；144最优审计/33证书、默认原10测试+新剖面测试共11/11（{elapsed:.2f}秒）及20180priority金标通过。\n\n同GCC15.2 Release O3/DNDEBUG原202三轮CPU比1.158333/1.091912/1.021567，逐pair中位增加9.19%；两侧中位21.250→22.203125秒为增加4.49%，不称整体加速。共同61失败CPU分别中位13.812500→15.359375秒；全部求解wall21.983504→22.445947秒、CLI22.998508→23.390441秒。新72的CPU比0.979730/0.942308/0.965986不能外推困难集。全部失败与恢复组费用见 `reports/resource-cost-summary-batch44.json`；root独立heap Event重放249合法计划已通过，早期pre-guard串行计划与最终8stream方案分别保留。\n\n单文件源 `{source}`，实际默认EXE `{m['default_exe_sha256']}`，性能测量EXE `{m['measured_exe_sha256']}`，两者来源与所有compile输入SHA分别冻结 `research/batch44/provenance.json`。R43冻结留作回退，旧R31报告保持，最新续研报告更新；prepare曾打印LF文本SHA，已改实际字节，功能证据一直采用actual read_bytes SHA。恢复搜索增加CPU换取可行性覆盖；继续针对61条未解结构探索，不声称官方全图保证/隐藏成绩/主办方资源时限。\n'''
for name in ['README.md','docs/TEST_READINESS.md','DEVELOPMENT_PLAN.md','solution/README.md']:
    p=Path(name);s=p.read_text(encoding='utf-8')
    if '第44批当前默认：' not in s:s+=text
    if name=='README.md':
        a=s.index('当前默认R43');b=s.index('\n\n',a);s=s[:a]+f'''当前默认R44保留R42整数修复与R43资源改动，并恢复6条记录（原困难2参数记录、新持出4种子）：1301记录1240按预期通过、61已知有解仍未解；原成功T/peak保持。原202逐pair中位CPU增加9.19%，这是可行性覆盖与CPU费用的取舍。144最优审计、523数值/2590剖面金标、20180评分金标、默认11/11测试通过。源 `{source}`。以下按批数字是历史冻结；最新见 [验证记录](docs/validation.json)、[续研报告](reports/project27-research-resumed.tex)；[R31报告](reports/project27-research.tex)保持旧冻结。'''+s[b:]
    p.write_text(s,encoding='utf-8')
p=Path('reports/research-batch44.md');s=p.read_text(encoding='utf-8');s=s.replace('当前仍为隔离候选，默认冻结 R43；同 Release 成本配对和默认验收尚待执行。','当前已晋升默认 R44，保留 R43 冻结回退；同 Release 成本配对和默认验收均已实际完成。')
s=s.replace('剩余12强资源界/默认 CTest验收留到成本窗结束后，不先声称144最终验收。','12强资源界另12/12精确通过，合计144最优审计/33证书；默认原10加新profile共11/11通过。')
s=s.replace('同 Release 成本窗尚未执行，失败搜索额外成本必须计入后再讨论默认推广。','同 Release 成本三轮已完成：202每pair CPU均增加，逐pair中位+9.19%，两侧中位+4.49%；共同61失败也计入。以恢复6记录为推广依据，不称整体加速。')
s=s.replace('当前尚未冻结默认 R44，不覆盖任何先前费用数字。','默认 R44 已真实冻结，所有compile输入、默认与测量EXE分别有SHA，不覆盖任何先前费用数字。')
p.write_text(s+text,encoding='utf-8')
print('Default',source,m['default_exe_sha256'],'CTest',elapsed,'manifest',sha('research/batch44/provenance.json'))
