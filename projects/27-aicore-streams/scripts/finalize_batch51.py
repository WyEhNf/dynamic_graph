"""Freeze actual promoted default after root authorization/build/14CTest/smoke.

Historical candidate evidence is reused with exact source SHA; only default
14CTest and ten smoke cases are newly executed after promotion, not full979.
"""
import hashlib
import json
import re
from pathlib import Path

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
p = Path('research/batch51')
source = sha('solution/solution.cpp')
acceptance = json.loads((p/'acceptance-checkpoint.json').read_text(encoding='utf-8'))
completion = json.loads((p/'paired-completion.json').read_text(encoding='utf-8'))
assert source == sha(p/'solution.cpp') == acceptance['source_sha'] == completion['source_sha']
ctest = Path('reports/ctest-default-batch51.txt').read_text()
assert '100% tests passed' in ctest and '14/14' in ctest
build = json.loads((p/'default-build-status.json').read_text(encoding='utf-8'))
assert len(build['statuses']) == 3 and all(row['actual_exit_code'] == 0 for row in build['statuses'])
smoke = json.loads(Path('reports/default-smoke-summary-batch51.json').read_text())
assert (smoke['count'],smoke['passing'],smoke['unresolved']) == (10,7,3)
assert smoke['source_sha'] == source and smoke['exe_sha'] == sha('build/aicore_bench.exe') == sha(p/'default-aicore_bench.exe')
cost = json.loads(Path('reports/resource-cost-summary-batch51.json').read_text())
assert cost['hard']['counts']['recovered'] == 1 and cost['heldout']['counts']['recovered'] == 0
unresolved = [dict(name=row['name'],n=row['n'],error=row['error']) for row in json.loads(Path('reports/hard-functional-batch51.json').read_text())['cases'] if not row['pass']]
held_unresolved = [dict(name=row['name'],n=row['n'],error=row['error']) for row in json.loads(Path('reports/heldout-functional-batch51.json').read_text())['cases'] if not row['pass']]
assert len(unresolved) == 57 and len(held_unresolved) == 6
inputs = ['solution/solution.cpp','CMakeLists.txt'] + [path.as_posix() for directory in ('src','include') for path in sorted(Path(directory).glob('*')) if path.suffix in ('.cpp','.h')]
tests = [path.as_posix() for path in sorted(Path('tests').glob('*.cpp'))]
flags = [f'build/CMakeFiles/{name}/flags.make' for name in ('solution.dir','aicore_bench.dir','simulator.dir')]
reports = ['reports/full-verification-batch51.json','reports/full-numeric-verification-batch51.json',
           'reports/functional-summary-batch51.json','reports/ctest-default-batch51.txt',
           'reports/build-default-batch51.txt','reports/default-smoke-summary-batch51.json',
           'reports/default-smoke-batch51.json','reports/resource-cost-summary-batch51.json']
m = dict(
    status='validated_remaining_direct_release_cut_default_milestone', source_sha256=source,
    default_exe_path='build/aicore_bench.exe', default_exe_sha256=sha('build/aicore_bench.exe'),
    default_archive='research/batch51/default-aicore_bench.exe',
    measured_exe_path=completion['candidate_exe_path'], measured_exe_sha256=completion['candidate_exe_sha'],
    performance_baseline_exe_path=completion['baseline_exe_path'], performance_baseline_exe_sha=completion['baseline_exe_sha'],
    old_default_R48_source_sha=sha('research/batch48/solution.cpp'),
    old_default_R48_exe_sha=sha('research/batch48/default-aicore_bench.exe'),
    old_R48_freeze='research/batch48/provenance.json',
    rollback_manifest_path='research/batch48/rollback/manifest.json', rollback_manifest_sha=sha('research/batch48/rollback/manifest.json'),
    compile_inputs={path:sha(path) for path in inputs}, test_inputs={path:sha(path) for path in tests},
    generation_inputs={path:sha(path) for path in [
        'solution/projection.cpp.inc','solution/release-cut.cpp.inc',
        'research/batch51/projection.cpp.inc','research/batch51/release-cut.cpp.inc',
        'scripts/prepare_batch51.py','scripts/make_release_cut_gold_batch51.py',
        'scripts/promote_batch51.py','scripts/verify_default_smoke_batch51.py','scripts/finalize_batch51.py']},
    release_flags={path:Path(path).read_text() for path in flags},
    candidate_acceptance_sha=sha(p/'acceptance-checkpoint.json'), candidate_acceptance=acceptance,
    paired_plan_sha=sha(p/'paired-plan.json'), paired_completion_sha=sha(p/'paired-completion.json'), paired_cost=cost,
    reports={path:sha(path) for path in reports}, independent_simulator_sha256=sha('src/simulator.cpp'),
    original_records=1229, original_passed_according_to_expectation=1172,
    prior_heldout_records=72, prior_heldout_passed=72, new_heldout_records=48,new_heldout_passed=42,
    total_records=1349,total_passed_according_to_expectation=1286,total_expected_infeasible=1,
    known_witness_unresolved_original=57,known_witness_unresolved_new=6,known_witness_unresolved=63,
    count_caveat='Parameter repeats and one expected-infeasible rejection retained;1286 expectation passes are not1286 feasible outputs;one newly recovered140-node original graph,fresh48 still42/48',
    hard_records=202,hard_legal=145,normal979_direct_R48_same_every_record=True,
    prior_structure36_same=True,prior_heldout72_same=True,resource_cliques12_same=True,
    recovery=dict(original_records=1,original_topologies=1,new_heldout_records=0,lost=0,common186_T_peak_identical=True),
    unresolved=unresolved,heldout_unresolved=held_unresolved,optimum_audits=144,optimal_certificates=33,
    ctest='14/14 actual exit0;all include tests target actual default51',
    ctest_shared_wall_seconds=float(re.search(r'Total Test time \(real\) =\s+([\d.]+)',ctest).group(1)),
    numeric_fixed_plan_gold=625,numeric_old_fixed=523,numeric_new_cut_fixed=102,release_cut_probe_gold=102,
    numeric_source='Exact8b7c candidate Clang21 actual625/495/83+210+102 already executed;promotion reruns actualGCC default14CTest including oldfixed/profile/group/102cut,not625Clang or979 again',
    workspace_profile_gold=495,shallow_profile_gold=2590,priority_gold=20180,
    group_recognition_gold=83,group_moved_profile_gold=210,default_smoke=smoke,
    single_file='problem.h plus standard library;reference fragments fully expanded and not compiler dependencies',
    support='Complete remaining original DIRECT consumers plus uncompleted ancestors;capacity/true lifetime aware;optionalcut128nodes/top24heldproducers/single deterministicgreedy;2M from original total16M,remaining R48 projection budget;no witness/family selection/edge rewrite',
    timing_caveat='Hard pairedmedianCPU-6.24%,side-median-6.07%,thirdpair+6.07% retained;freshCPU-2.90% butwall+0.46%;12hostCPURAMsampled including user background,not OS-isolated or stableuniversal speedup',
    old_frozen_R31_tex_sha=sha('reports/project27-research.tex'))
assert m['old_frozen_R31_tex_sha'] == acceptance['old_user_open_tex_sha']
for name in ('reports/final-checkpoint-batch51.json','research/batch51/provenance.json'):
    Path(name).write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
validation = Path('docs/validation.json')
data = json.loads(validation.read_text(encoding='utf-8'))
data['latest_default_checkpoint'] = m
data['remaining_direct_release_cut_batch51'] = m
validation.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
text = f'''

第51批当前默认：在R48基础上新增完整remaining-DIRECT用户祖先释放cut；Compute BEGIN W+O、最后原DIRECT消费者END释放、cut外用户/sink保留、原边和硬件/截止不改。2M新阶段来自原16M总预算，最多128节点/top24持出producer/单一确定性greedy，不增加种子或预算。原202困难144→145，新增140节点原图T1430270恰好deadline、peak2481<=2483；186共有成功T/peak恒等、0丢失，新48仍42/48，57+6共63已知可行未解显式保留。合计1349记录1286按预期通过，含1预期不可行拒绝与参数重复，不是1286合法可行输出。

候选实际1099条直接R48回归逐record相同（979+36+72+12），625固定计划/495闭包/83识别+210移动/102cut独立bigint及ClangUBSan通过。首次C盘ENOSPC构建exit1历史保留，仅编译子进程TEMP/TMP/TMPDIR改项目F-temp重试exit0，未清用户文件或改系统环境。推广后actual默认14/14 CTest（{m['ctest_shared_wall_seconds']:.2f}秒共享功能）及10烟测7合法（4恢复+3正常）/3已知可行未解匹配已验收候选，未重新跑979或完整性能。

唯一同Release54fc→25ac完整202+48各3轮/12trial/1500case执行：困难全CPU比0.857803/0.937605/1.060692，paired中位-6.24%、side中位-6.07%，第三轮+6.07%保留；新48 CPU中位-2.90%，solve墙时+0.46%。每trial原始宿主CPU ticks/RAM起止+0.25秒采样均measured，包含用户背景、不扣除背景，非OS隔离，不称稳定通用加速。全部失败成本分组保留。actual默认EXE `{m['default_exe_sha256']}` 与实测EXE `{m['measured_exe_sha256']}` 分开；源 `{source}`，清单 [provenance](research/batch51/provenance.json)。R48完整回退档在 `research/batch48/rollback/manifest.json`，用户旧R31打开TeX严格保持。R49扩组/50first pivot不混入默认；R50曾改善共同131峰1946→1884但0新增恢复，独立负结果仍保留。
'''
for name in ('README.md','docs/TEST_READINESS.md','DEVELOPMENT_PLAN.md','solution/README.md','reports/research-batch51.md'):
    path = Path(name)
    current = path.read_text(encoding='utf-8')
    if '第51批当前默认：' not in current:
        current += text
    if name == 'README.md':
        start = current.index('当前默认R48')
        end = current.index('\n\n',start)
        current = current[:start]+f'当前默认R51原202困难145/202，比R48新增1条完整140节点原图恢复；新48仍42/48，57+6共63已知有解未解。1349记录1286按预期通过，含1预期不可行拒绝及参数重复。1099直接R48回归、625固定计划数值/495闭包/83识别210组移动/102cut金标、actual默认14/14 CTest与10烟测通过。完整失败成本保留，困难CPU配对中位-6.24%但第三轮+6.07%，新48wall+0.46%，不称稳定通用加速。源 `{source}`。以下批次数字为历史冻结；最新见 [验证记录](docs/validation.json)、[续研报告](reports/project27-research-resumed.tex)，[R31报告](reports/project27-research.tex)严格保持旧冻结。'+current[end:]
    path.write_text(current,encoding='utf-8')
print('Actual default51 frozen',source,m['default_exe_sha256'],'manifest',sha(p/'provenance.json'),flush=True)
