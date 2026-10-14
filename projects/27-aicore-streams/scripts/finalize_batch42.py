import hashlib,json,shutil
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('solution/solution.cpp')==sha('research/batch42/solution.cpp')
assert sha('src/simulator.cpp')==sha('research/batch42/simulator.cpp')
shutil.copyfile('build/aicore_bench.exe','research/batch42/default-aicore_bench.exe')
hard=json.loads(Path('reports/hard-corpus-batch42.json').read_text());failed=[x for x in hard['cases'] if not x['pass']]
reg=json.loads(Path('reports/regression-batch42.json').read_text())
manifest=dict(status='validated_correctness_default_milestone',source_sha256=sha('solution/solution.cpp'),independent_simulator_sha256=sha('src/simulator.cpp'),default_exe_sha256=sha('build/aicore_bench.exe'),candidate_exe_sha256=sha('research/batch42/aicore_bench.exe'),normal_records=1229,normal_passed_according_to_expectation=1166,normal_expected_infeasible=1,known_witness_unresolved=63,hard_records=202,hard_legal=139,new_structure_records=36,new_structure_legal=36,normal_vs_R39='same pass/T/peak per record; no losses, no recovery; arithmetic correction only',strict_regression_records=979,strict_regression_wall_seconds=reg['elapsed_wall_seconds'],optimum_audits=144,optimal_certificates=33,ctest='10/10 passed, 2.33s',numeric_fixed_plan_gold=523,numeric_fixed_plan_legal=209,numeric_fixed_plan_expected_rejection=314,priority_arbitrary_precision_gold=20180,compiler='GCC15.2 C++17 standalone -O2 -Wall -Wextra -Wpedantic no warnings; Clang21.1 VS2022 UBSan fixed-plan/priority paths no diagnostics',hard_single_functional_solve_wall_us=sum(x['solve_us'] for x in hard['cases']),hard_single_functional_thread_cpu_us=sum(x['solve_thread_cpu_us'] for x in hard['cases']),failed63_single_functional_wall_us=sum(x['solve_us'] for x in failed),failed63_single_functional_thread_cpu_us=sum(x['solve_thread_cpu_us'] for x in failed),timing_caveat='Single functional regression, no paired speedup claim; Win32 thread CPU quantized',unresolved=[dict(name=x['name'],n=x['n'],error=x['error']) for x in failed],scaled_witness_count=32,scaled_solver_legal=26,scaled_solver_unresolved=6,scaled_caveat='All 32 fixed witnesses valid and exact gold matched; solver restoration is separate, saturation of priorities may alter traversal',old_R39_caveat='Historical normal-range performance checkpoint; R39 and prior simulators had reproduced signed overflow near int64 limits. Frozen artifacts retained, no full-range correctness claim.',old_frozen_R31_tex_sha256=sha('reports/project27-research.tex'),old_R41_resource_candidate='separate/unpromoted; must rebase onto R42 before performance assessment')
inputs=['data/numeric-controls-batch42.json','data/scaled-serial-controls-batch42.json','data/numeric-parallel-batch42.json','data/numeric-parallel-valid-batch42.json','data/priority-gold-batch42.txt']
manifest['input_sha256']={p:sha(p) for p in inputs}
Path('research/batch42/provenance.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
Path('reports/final-checkpoint-batch42.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
p=Path('docs/validation.json');v=json.loads(p.read_text(encoding='utf-8'));v['latest_default_checkpoint']=manifest;v['numeric_correctness_batch42']=manifest;p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
text=f'''\n\n第42批当前默认：只修复非负int64边界，不混入R41资源优化。真实显存先扣剩余容量再分配；时间加法/Wait乘法显式检查，MAX合法定时器与“无定时器”分离；小图DP用独立可达标记；前沿持出量只对待完成目标精确累加/撤销；评分乘后除采用标准库整数精确运算后饱和。没有全图历史output总量上限，原直接消费者释放和sink保留保持。源SHA-256 `{manifest['source_sha256']}`，独立模拟器 `{manifest['independent_simulator_sha256']}`，默认bench `{manifest['default_exe_sha256']}`。\n\nClang21.1/VS2022 UBSan已分别复现旧R39两模型6e18+6e18溢出；R42拒绝超容量并接受峰值/完成时刻恰MAX。523条独立Python大整数固定计划金标（209合法、314预期拒绝）及20180个完整乘后除评分金标通过、无UBSan诊断；32个放大后历史output总和超过MAX的witness全部准确匹配，但求解器只恢复26/32，另外6条不算模型失败或已求出。\n\n979严格回归40.373秒、144最优标尺/33证书、1120前沿检查与CTest10/10（2.33秒）通过。202困难仍139合法/63有witness未解，新36结构36合法；全部正常记录相对R39 pass/T/peak逐条相同。正常1229记录1166按预期通过（含1预期不可行及参数重复），边界语义控制单独计数，不夸成新增可行图恢复或CPU加速。完整冻结与全部失败单次求解成本见 `reports/final-checkpoint-batch42.json`、`research/batch42/provenance.json`。R31/R39历史文件保留；旧R39正常范围配对不代表完整int64正确性。\n'''
for name in ['README.md','docs/TEST_READINESS.md','DEVELOPMENT_PLAN.md','solution/README.md']:
 p=Path(name);s=p.read_text(encoding='utf-8');p.write_text(s+text,encoding='utf-8')
p=Path('README.md');s=p.read_text(encoding='utf-8');a=s.index('最终状态：');b=s.index('\n\n',a);s=s[:a]+f'''当前默认R42已修复完整非负int64边界：正常1229记录1166按预期通过、63条有witness仍未解；144独立最优标尺、523条独立大整数固定计划金标、20180评分金标、CTest10/10及单文件编译通过。源 `{manifest['source_sha256']}`。以下按批数字为冻结历史，最新证据见 [验证记录](docs/validation.json) 与 [续研报告](reports/project27-research-resumed.tex)；[R31报告](reports/project27-research.tex)保留旧冻结版本。'''+s[b:];p.write_text(s,encoding='utf-8')
p=Path('DEVELOPMENT_PLAN.md');s=p.read_text(encoding='utf-8').replace('## 当前验收结果','## 最初基座验收结果（当前R42见末尾）',1);p.write_text(s,encoding='utf-8')
p=Path('requirements.md');s=p.read_text(encoding='utf-8');s=s.replace('核心需求不超过128；计算时长1至1e9；事件时长0至1e6；显存量级至1e9。模拟时间及内存使用int64。','核心请求1至128且不超过对应池；计算时长1至1e9。公开说明常见事件/显存量级为1e6/1e9；本地转录接口的显存与Event字段均为非负int64，当前实现和边界控制覆盖至INT64_MAX，未人为增加量级上限。显存总和先检查剩余容量，绝不饱和后当作可容纳；时间/Wait总和超int64范围的方案明确拒绝（无法满足int64 deadline）。');p.write_text(s,encoding='utf-8')
p=Path('reports/project27-research-resumed.tex');s=p.read_text(encoding='utf-8');s=s.replace('979严格回归、144标尺和5项CTest通过；旧R31文件保持不变。','R42另修复完整非负int64边界，两旧模型的共同溢出由UBSan独立复现。\n979严格回归、144标尺、523条大整数固定计划金标及10项CTest通过；旧R31文件保持不变。');s=s.replace('最新验证默认R39源SHA-256为','正常范围历史验证默认R39源SHA-256为');section=r'''
\section{R42：独立整数正确性修复}
R39两套C++状态机在普通量级一致，但这种一致不能排除共同算术错误。
硬件显存为\texttt{INT64\_MAX}、单节点workspace与output各为
$6\cdot10^{18}$时，真实同时占用超过容量；旧模型把有符号加法溢出后的量当成可分配。
Clang 21.1、VS2022运行库的UBSan分别在独立模型和提交模型中实证同一问题。
原冻结R31/R39数字保留为正常量级历史证据，不再推断完整整数域正确。

实际占用采用逐项剩余容量检查，通过后才作精确加法；不能把真实量饱和后再减去释放量。
时间加法与Wait数量乘时长先检查可表示性，\texttt{INT64\_MAX}合法定时器与不存在定时器用独立布尔状态区分。
串行子集DP也分开可达状态与最大合法峰值。
前沿持出量仅为尚未完成目标维护，按真实动作对称撤销；已完成目标不累计历史输出。
评分乘法先作标准库整数乘除分解，精确除法完成后才饱和，避免乘1024溢出。
直接父输出与最终sink之和可构成必要拒绝门槛；全部节点历史output之和不能成为上限。

独立Python任意精度Event模型及原始边串行递推生成固定计划金标。
523条控制包含209合法、314预期拒绝，覆盖恰好最大峰值与完成时间、超容量、多父输入、
Wait乘法、异构核争抢、乱序ID、历史输出超过最大值但已释放。
另20180个完整乘后除的评分控制与Python大整数一致。
这些控制及评分路径在UBSan下通过；默认CTest增为10项，全部通过，墙时2.33秒。
32条放大图的固定witness全部正确，但求解器只求出26条，另6条仍保留为启发式缺口，
不混入语义测试成功数。通常量级1229记录仍1166按预期通过、63已知有解未解；
202困难及新36结构的全部pass/T/peak与R39逐条相同。
979严格回归40.373秒、144最优标尺及33证书保持；这是单次功能验证，不是配对加速证据。
R41流式best/显式emit资源候选继续隔离，必须基于R42修复重建再评估成本。

当前R42源SHA-256：\path{96d31657a8ab4a432c6f0fee14ac835d99b9806a04839adb5409751406dfeb1a}。
完整冻结、输入SHA及全部63失败单次求解成本见\path{research/batch42/provenance.json}，
控制入口见\path{tests/test_numeric.cpp}和\path{tests/test_numeric_priority.cpp}。
旧R31单文件报告保持原SHA，尚无官方包、隐藏评分或真实NPU验证。
'''
s=s.replace('\\begin{thebibliography}{99}',section+'\n\\begin{thebibliography}{99}');p.write_text(s,encoding='utf-8')
print('R42 default',manifest['default_exe_sha256']);print('new TeX',sha('reports/project27-research-resumed.tex'));print('single hard all/fail CPU',manifest['hard_single_functional_thread_cpu_us'],manifest['failed63_single_functional_thread_cpu_us'])
