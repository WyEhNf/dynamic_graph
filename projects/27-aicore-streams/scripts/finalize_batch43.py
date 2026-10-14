"""Freeze R43 only after saved functional, bigint and paired evidence exists."""
import hashlib,json,re,shutil,statistics
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=sha('solution/solution.cpp');assert source==sha('research/batch43/solution.cpp')
assert Path('research/batch42/solution.cpp').read_text(encoding='utf-8').split('std::vector<int> strict_fork_join_order(')[0]==Path('solution/solution.cpp').read_text(encoding='utf-8').split('std::vector<int> strict_fork_join_order(')[0]
ctest=Path('reports/ctest-batch43.txt').read_text(encoding='utf-8');assert '100% tests passed' in ctest
elapsed=float(re.search(r'Total Test time \(real\) =\s+([\d.]+)',ctest).group(1))
rows=[];reg=json.loads(Path('reports/regression-batch43.json').read_text())
for name in reg['comparisons']:
 oldp=Path(f'reports/{name}-batch42.json');newp=Path(f'reports/{name}-batch43.json');a={x['name']:x for x in json.loads(oldp.read_text())['cases']};b={x['name']:x for x in json.loads(newp.read_text())['cases']};assert a.keys()==b.keys()
 assert all((a[k]['pass'],a[k]['T'],a[k]['peak_memory'])==(b[k]['pass'],b[k]['T'],b[k]['peak_memory']) for k in a)
 rows.append(dict(suite=name,records=len(a),before=str(oldp),after=str(newp),before_sha=sha(oldp),after_sha=sha(newp)))
Path('reports/direct-normal-r42-batch43.json').write_text(json.dumps(dict(records=979,all_same=True,baseline_sha=sha('research/batch42/solution.cpp'),current_sha=source,historical_regression='batch8..22 sources; direct frozen R42 comparison is separate',suites=rows),indent=2))
for label in ['numeric-controls','numeric-parallel','numeric-parallel-valid','scaled-serial']:
 r=json.loads(Path(f'reports/{label}-ubsan-batch43.json').read_text());assert r['passed']==r['total']
old=json.loads(Path('reports/final-checkpoint-batch42.json').read_text());m=dict(old)
m.update(status='validated_equivalent_resource_default_milestone',source_sha256=source,default_exe_sha256=sha('build/aicore_bench.exe'),paired_candidate_exe_sha256=sha('research/batch43/default-style-aicore_bench.exe'),R42_independent_simulator_sha256=sha('src/simulator.cpp'),strict_regression_wall_seconds=reg['elapsed_wall_seconds'],ctest=f'10/10 passed, {elapsed:.2f}s',normal_vs_R42='all pass/T/peak identical; 979 direct cached reports + hard202/structure36 every paired round + 12 exact optima',paired_hard='reports/resource-cost-hard-batch43.json',paired_structure='reports/resource-cost-forkjoin-batch43.json',changes=['Streaming stable best macro in greedy mode','Full bitset exact pending-set deduplication','Strict fork/join branch-choice record and explicit emit'],same_search_budget=True,paired_flags='Both GCC15.2 CMake Release -O3 -DNDEBUG; same local harness and independent R42 simulator',numeric_validation='523 fixed-plan bigint gold on Clang21 UBSan passed; unchanged priority prefix also checked by default 20180 exact gold CTest',function_equality=dict(frontier=1120,macro_trajectory=332,strict_structural_order=105),R41_status='isolated unpromoted predecessor; R43 rebased exactly on R42 fixes',numeric_caveat='Scaled32 fixed-plan gold all valid; solver26/32, six unresolved retained',count_caveat='Normal1229 includes repeated parameter records and one expected-infeasible; bigint523 counted separately, not extra restored topologies')
for family in ['hard','forkjoin']:
 p=Path(f'reports/resource-cost-{family}-batch43.json');cost=json.loads(p.read_text());m[family+'_paired_cost']=cost
m.pop('hard_single_functional_solve_wall_us',None);m.pop('hard_single_functional_thread_cpu_us',None);m.pop('failed63_single_functional_wall_us',None);m.pop('failed63_single_functional_thread_cpu_us',None)
m['strict_regression_baseline']='Historical8..22 no regression; direct frozen R42 existing reports 979 full equality'
m['direct_normal_R39_evidence']='R42 direct R39 proof retained; R43 direct R42 proof reports/direct-normal-r42-batch43.json'
m['old_R42_candidate_exe_sha256']=m.pop('candidate_exe_sha256')
m['measured_exe_sha256']=m['paired_candidate_exe_sha256']
m['normal_vs_R39']='Transitive normal-range equality: archived R39/R42 direct reports, then R42/R43 direct cached979 and paired202/36; R43 contains three equivalent storage/order changes in addition to R42 arithmetic fixes'
m['priority_gold_execution']='R43 default CTest numeric_priority_exact_gold actually reran all20180 Python-bigint gold rows; R43 Clang fixed-plan523 reran separately. Historical R42 UBSan priority execution is retained, not counted as a fresh R43 UBSan priority run.'
shutil.copyfile('build/aicore_bench.exe','research/batch43/default-aicore_bench.exe')
Path('research/batch43/provenance.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8');Path('reports/final-checkpoint-batch43.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
p=Path('docs/validation.json');d=json.loads(p.read_text(encoding='utf-8'));d['latest_default_checkpoint']=m;d['equivalent_resource_batch43']=m;p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
text=f'''\n\n第43批当前默认（第42批整数修复保留）：只减少等价路径的资源开销，贪心只保存稳定最小宏、pending闭包用完整bitset判同、严格fork/join保存分支选择后显式emit；闭包仍来自同一g.topo，tie仍保留最早，8M预算/n≤768前沿/结构n≤4096及depth≤512保持。源SHA `{source}`，默认EXE `{m['default_exe_sha256']}`，实际配对候选EXE `{m['paired_candidate_exe_sha256']}`，冻结 `research/batch43/provenance.json`。结构识别与输出均O(n)，递归识别深度上限未变；不能据此宣称全CLI RAM下降。\n\n332宏轨迹、105结构order对照和1120独立前沿检查通过；523大整数固定计划金标真实R43源码Clang UBSan通过、无诊断；默认20180评分金标通过。979对历史8–22基线无退化，另直接读取R42/R43逐记录979 pass/T/peak全同（`reports/direct-normal-r42-batch43.json`）；144最优标尺/33证书、CTest10/10（{elapsed:.2f}秒）通过。普通1229仍1166按预期通过、63有witness未解；202困难三轮139/63、新36三轮36/0，全部逐record质量同R42，0恢复/0丢失。\n\n三轮202逐配对CPU比0.992487/0.942689/0.979433，中位改善2.06%，改善范围0.75–5.73%；分别取before/after中位的21.265625→20.046875秒比才是5.73%，不将它当典型每对收益。全wall分别中位21.976112→20.593606秒、CLI23.042063→21.653200秒；共同63失败CPU分别中位14.015625→13.187500秒，完整成本包含全部失败。候选最大全CLI工作集316633088字节约302MiB，没有RAM显著下降证据。\n\n36结构逐配对CPU比1.060241/0.964286/0.942529，一轮变慢；分别中位CPU1.3125→1.28125秒，wall1.284990→1.304146秒、CLI1.420676→1.436414秒略增，保留负结果，不称稳定结构加速。两版统一CMake Release -O3/-DNDEBUG，详见 `reports/resource-cost-hard-batch43.json`、`reports/resource-cost-forkjoin-batch43.json` 及三轮原始paired文件。资源优化没有解决63条可行图缺口，后续先做浅层producer/consumer结构适用率与有数学依据的恢复分支；不改witness/困难集合/测试口径。\n'''
for name in ['README.md','docs/TEST_READINESS.md','DEVELOPMENT_PLAN.md','solution/README.md']:
 p=Path(name);s=p.read_text(encoding='utf-8');
 if '第43批当前默认（' not in s:s+=text
 if name=='README.md':
  a=s.index('当前默认R42');b=s.index('\n\n',a);s=s[:a]+f'''当前默认R43保留R42完整非负int64修复：正常1229记录1166按预期通过、63条有witness仍未解；144最优标尺、523大整数固定计划金标、20180评分金标与CTest10/10通过。三轮202资源配对逐对CPU改善中位2.06%，全部方案质量保持；36结构墙时略增，记录负结果。源 `{source}`。以下按批数字为冻结历史，最新证据见 [验证记录](docs/validation.json) 与 [续研报告](reports/project27-research-resumed.tex)；[R31报告](reports/project27-research.tex)保持旧冻结。'''+s[b:]
 p.write_text(s,encoding='utf-8')
p=Path('reports/project27-research-resumed.tex');s=p.read_text(encoding='utf-8');s=s.replace('R42另修复完整非负int64边界，两旧模型的共同溢出由UBSan独立复现。','R42另修复完整非负int64边界，两旧模型的共同溢出由UBSan独立复现。\nR43在相同搜索路径上减少存储与顺序拼接开销；202逐配对CPU改善中位2.06\\%，36结构墙时略增。')
s=s.replace('当前R42源SHA-256：','整数正确性历史R42源SHA-256：')
section=r'''
\section{R43：等价资源改动与成本的两种中位口径}
贪心原本按$(final\_live,peak)$稳定排序后只用首项；现在逐候选维护严格更小的best，
相等保留最早项，所有候选仍按原顺序模拟。闭包均由同一$g.topo$过滤，
故pending节点向量与完整节点bitset一一对应；去重集合只判插入，不以集合顺序挑选。
严格fork/join递归只保存原选择的first/second/root/join，之后显式栈顺序输出。
识别和emit均为$O(n)$，支持范围与递归深度上限保持。
不引入新搜索、扩大预算或改变Event/直接消费者释放。

332个宏order/work/失败状态/截断对照、105结构order对照和1120前沿检查通过。
523大整数固定计划控制在真实R43源Clang UBSan下通过，默认20180评分金标通过。
979对历史批8--22无退化；另读取冻结R42/R43逐记录报告证明979结果全同。
144最优标尺、33证书及CTest10/10通过。
202困难三轮均139合法/63未解，新36三轮均36合法；每轮全部pass/T/peak相同。

\begin{tabularx}{\textwidth}{L{4.0cm}rrX}
\toprule
指标 & Before & After & 口径与限制\\
\midrule
202全部线程CPU/秒 & 21.265625 & 20.046875 & 分别取两侧中位，比值改善5.73\%\\
202全部求解wall/秒 & 21.976112 & 20.593606 & 全部成功与失败\\
63共同失败CPU/秒 & 14.015625 & 13.187500 & 分别中位，包括未解搜索\\
36结构线程CPU/秒 & 1.312500 & 1.281250 & 量化测量，一轮变差\\
36结构wall/秒 & 1.284990 & 1.304146 & 略增，保留负结果\\
\bottomrule
\end{tabularx}

独立侧中位之比与逐配对比值的中位不是同一统计量。
202三轮逐对CPU比为0.992487、0.942689、0.979433，改善0.75--5.73\%，
逐对改善中位仅2.06\%；不能把5.73\%写成典型每对收益。
36逐对CPU比为1.060241、0.964286、0.942529，一轮变慢；
全CLI墙时分别中位1.420676到1.436414秒，也略增。
两版均GCC15.2、CMake Release的\texttt{-O3 -DNDEBUG}，相同harness与R42独立模型。
202候选全CLI最大工作集316633088字节约302MiB，JSON及验证开销也在内，
没有证据称整个进程RAM显著下降。
原始逐轮与两种中位口径分别见
\path{reports/resource-cost-hard-batch43.json}、\path{reports/resource-cost-forkjoin-batch43.json}。

R43正常1229记录仍1166按预期通过，63已知有解未解，资源改动不是可行性恢复。
当前默认源SHA-256：\path{e7c3f2cc84098f5da051265eddc1dc5a0cdc59c464ab0078c346a9888801c6eb}。
实际配对候选与默认构建二进制的SHA分别保存，见\path{research/batch43/provenance.json}。
旧R31/R39/R42冻结不覆盖；后续将先评估浅层消费者窗口的适用率再实施恢复候选。
'''
if '\\section{R43：' not in s:s=s.replace('\\begin{thebibliography}{99}',section+'\n\\begin{thebibliography}{99}')
p.write_text(s,encoding='utf-8');print('R43 default exe',m['default_exe_sha256']);print('R43 Tex SHA',sha(p));print('ctest',elapsed)
