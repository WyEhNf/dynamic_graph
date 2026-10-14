# R45：有偏序的 workspace 接口闭包候选

当前仍以 R44 为默认。本候选新增两个原困难记录的可行输出，隔离候选完整验收已完成，同 flags 成本配对和默认晋升尚未进行。两个记录属于同一拓扑的 root 输出参数变化；新的 48 个独立种子记录尚无新增恢复。

## 研究依据与模型边界

[Jin 等的原始论文](https://arxiv.org/html/2312.13526v1) 第 4 节的 computation graph 同时包含 scratch/output，第 5 节的线性化要求 isolated subgraph 与 dominant profile。一般密集共享 DAG 不满足这些前提，不能把单个子图最小 peak 次序随意压成宏任务。本候选没有采用该最优线性化结论。

[Ahn 等的 SERENITY 原论文](https://arxiv.org/abs/2003.02369) 研究不规则网络的顺序内存规划与图重写。本题要求完整原图直接消费者生命周期，不能采用重写释放、重新计算、换页或以第三方 DP 最优性覆盖异构 Event 调度。

本候选仅把 workspace 汇合点用作顺序接口，闭包仍逐个执行原始节点。每个 BEGIN 同时分配 W+O；每个 END 释放 W，以及该时刻已完成最后直接消费者的父节点 O；最终输出一直保留到图完成。目标点间的保留输出依赖仍参与偏序约束。完整候选继续经过独立 AIC/AIV 核数、Wait/Record、deadline 和显存校验。串行 profile 没有为跨流并发提供最优保证。

## 输入识别和负结果

首先检测严格可连续合并的边：outdegree(u)=1 且 indegree(v)=1。全 202 条困难记录没有这种边。因此无法通过这种严格链压缩扩大 R44 的独立层识别范围。当前 61 个失败图虽有 1,721 个 indegree=outdegree=1 节点，但它们常处在 fanout/fanin 边界，单节点度数不等于可连续合并边。负结果保存在 `chain-window-classification-batch45.json` 和 `projection-input-classification-batch45.json`。

新接口识别只读取节点与原始依赖：fanin 至少 2，workspace 不小于非零 workspace 中位值的 4 倍（安全饱和阈值），且严格大于每个直接父节点 workspace。数量限制 2–512、图规模最多 4096。该阈值是启发式，不能说明未被选择的节点可删除，也不读取名称、生成器阶段、witness 或 seed。原 61 个未解记录中 35 个适用、26 个不适用。

对每个接口点，计算在其他接口点处停止的实际祖先闭包，并提取接口偏序。偏序 Kahn 次序按请求 permutation 优先级规范化，再依次展开尚未完成的闭包；最后执行原拓扑序中所有剩余节点。目标间非独立依赖仍约束 permutation。

初态来自原图排序、实际闭包共享输出权重、bundle 与内存排序；局部移动调整目标点次序。所有 profile 用精确双 uint64 表达，按照 excess/peak/area 比较，并以原直接后继计算释放。16M 收费工作上限包括 profile、normalization 估计与部分 affinity 比较，不等于整段 CPU 指令上限；闭包识别、现有 seed 排序与容器成本另有开销。原 61 诊断中 31 次耗尽收费预算，未解不构成不可行证明。

## 实际结果

隔离 diagnostic 在 61 个原 R44 失败输入上恢复两个串行计划。输入文件剥去 witness/generation，只包含 name/hardware/nodes/deadline，且原图数据未改变。

| 原记录后缀 | 节点/接口点 | T (us) | peak / capacity (B) |
|---|---:|---:|---:|
| dense_k12_ret1_seed20262235_rootmem0 | 71 / 21 | 1487053 | 1745 / 1747 |
| dense_k12_ret1_seed20262235_rootmem5 | 71 / 21 | 1487053 | 1760 / 1762 |

完整 failed-only 集成后的原 202 功能批为 **141→143**，共同可行 141 条全部 T/peak 恒等，0 丢失、0 模型分歧，**59 已知 witness 有解记录仍未解**。两条恢复输出仍为单流，未宣称时间最优。新 48 个未筛选的 retained-sharing 种子图为 **42→42**，共同 42 条 T/peak 恒等，6 条未解，0 新恢复。这项持出负结果保留。

新图生成器预先规定种子、规模、local/dense/global 连接、非零 roots 输出、workspace 偏移和 Event 大小。修改存储后先以无限容量独立重放原构造序，重算 peak 再设置 capacity；早期用旧 capacity 重放造成的生成阻塞已修正，没有按求解器结果删种子。

独立 Python 金标用完整祖先集合推导偏序，逐 BEGIN 以 prefix/future live 集合重新求和，没有复用 C++ 的 target-stop 闭包或可变用户计数。**495 个 order/permutation/profile/capacity 控制通过 GCC 与 Clang UBSan**，包含显式 O=0、多根多 sink、共享父节点、保留链、int64 边界和超 MAX 的瞬时 profile。Clang 构建的 UCRT LNK4217 链接警告与运行时 UB 分开记录；实际运行没有 UBSan runtime error。

完整功能 session 89079 实际 exit0，三次 CLI 总共享墙时 46.189536 秒。新候选为 O2、旧默认为 O3，期间共享 CPU，**不以该时间或 solve_thread_cpu_us 推导性能收益**。后续同 Release 成本窗口须单独冻结、协调与执行。

## 复现与冻结

- `research/batch45/solution-diagnostic.cpp`：0317c09ee7a7efc0e95224f1afb1557259bcd6191c4e878328bccb7e1df393b2。
- `research/batch45/solution.cpp` 完整候选：5116d8d9c859662a26d1aba7dd1b0916097cb2bd87e466007adf2cbede391dd9。
- `research/batch45/projection.cpp.inc`：2931f2dd9da53a2f7623aaa9d3460a1c79eb07eb457f3091c65525a0a58491f1；内容已完整展开，提交单文件无需 inc。
- 功能 EXE：6568a4543f212eb047cb88ed47c4cc28ebb737897f98439d6cba9dae16ebed88。
- `functional-provenance.json` 区分 diagnostic、GCC profile EXE、集成源和默认源；UBSan 使用集成源，profile helper 内容相同。
- `scripts/validate_batch45.py`；`reports/functional-summary-batch45.json`；三份 `*-functional-batch45.json` 全部保存失败和实际 plan。
- `scripts/make_projection_gold_batch45.py` 与 `reports/projection-profile-ubsan-batch45.txt`；`scripts/make_projection_holdout_batch45.py`。

默认 R44 文件与旧研究报告均未覆盖。下一步需找出持出六个失败图中 profile 的局部最小与接口偏序限制，而不是只普遍扩大预算；任何后续候选另存批次以保留当前因果比较。

## 完整候选验收补充（当时默认未晋升）

`reports/full-verification-batch45.json`记录一次授权的979按预期全通过，与R44按原始记录顺序逐条比较name/pass/valid/T/peak完全恒等（不只按name建字典）。原36结构、新72持出和12资源clique也全通过、T/peak恒等；132外部最优检查/21证书实际重新审计通过。979共享功能墙时64.328秒不表示性能变化。

隔离 CMake 将所有直接 include 测试镜像重定向到 `research/batch45/solution.cpp`，避免误测默认R44。顺序Release构建session21439实际exit0，**12/12 CTest**实际exit0（6.10秒共享功能墙时），涵盖523数字计划、20180优先级金标、2590浅层金标及495新workspace金标。原根目录CMake/默认源没有改动。

Clang21实测该完整候选源的**523固定计划控制**通过，0runtime UB。编译session76489 actual exit0。包装器第一次在11/11 driver已exit0后误读输出键`match`（实际为`pass`），报KeyError；修复后复用这11个同次结果，其余512个一次新执行。测试期望及原始报告未改。495 workspace UBSan复用此前已对同5116源码实际执行的冻结证据，未冒称重复执行。

完整验收冻结 `research/batch45/acceptance-checkpoint.json` SHA：

`4720682c975a17f5cf1cda4b73f2e4c9d9b8fe9af5e6a4d0d288d78bf02a3ff8`

实际隔离Release与另存 `research/batch45/release-candidate-frozen-aicore_bench.exe` 字节相同SHA：

`3e8273e29d090a99f8224dad8e7a47cd6c5d313e50bee026e4064ed200cb02a9`

验收结束时先冻结声明计划：`research/batch45/paired-plan.json` SHA `43ebc687b73bc3dfb23cc3a7a44a89aa818c91eb983763405e9597f05a2d34cf`，R44/R45同GCC15.2 Release，原202和完整新48各三轮交替，全部失败保留。随后经 root 协调、项目19 phase2终态后执行，实际结果见下文。声明文件没有回写成终态；完整质量与CPU费用分开判断后才讨论晋升。

## 上述计划的实际三轮成本终态（成本确认前默认未晋升）

原计划文件保持声明时的字节与 SHA；以下是其后实际执行结果。session **9393 actual exit0**，脚本完整 CLI 墙时 **235.4763402 秒**，202 与 48 各三轮交替全部终态。此轮实际基线是 `research/batch44/default-aicore_bench.exe` **7861a413…**，候选是冻结 Release **3e8273e2…**，同 GCC15.2/O3/Release flags；不能把它与 R44 上一成本批实际 EXE **8d43bf1f…**混为同一测量。

原 202 每轮 **141→143**、共同 141 条 T/peak 恒等、共同失败 **59** 条、恢复 **2** 条。全体 thread CPU 后/前分别 **1.104112、1.090299、1.134837**，逐配对中位 **+10.41%**；独立前后 CPU 中位同样 **30.015625→33.140625 秒，+10.41%**。全体 solve wall 配对中位 **+9.32%**，完整 CLI 的独立前后中位 **33.71784→37.16851 秒**。共同失败 CPU 独立中位 **20.359375→23.281250 秒**，没有剔除失败搜索。CLI 最大 working set 前/后 **317009920/316801024 字节**，包含 JSON、保存计划和验证器，不能称算法独占内存。

新 48 每轮 **42→42**、共同 42 条 T/peak 恒等、共同失败 **6** 条、恢复 **0**。全体 CPU 后/前分别 **1.075145、1.087209、1.093407**，逐配对中位 **+8.72%**，独立前后中位 **2.703125→2.921875 秒，+8.09%**；全体 solve wall 配对中位 **+6.62%**。这组代价没有带来新的恢复，不能把它称为持出质量成果或加速。

实际记录包括 Win32 当前线程 CPU（有量化）、每图 solve wall、完整 CLI wall 和 PeakWS。**每 trial host_busy/host_available 未测**；授权前的低可用 RAM 与用户后台应用观察不代表完整窗口采样，也不据此声称整机空闲。本次不补跑测量以美化背景。`reports/resource-cost-{hard,heldout,summary}-batch45.json` 保留每轮原始 SHA、分组费用、两个中位口径与实测 EXE/source SHA，父任务将独立复算后决定是否把额外可行性覆盖作为默认升级。


第45批当前默认：单文件workspace前沿/原始祖先闭包恢复，仅旧R44搜索失败后触发，不读witness/名字/seed。原202困难141→143，新增2条仍是同一拓扑的显存参数变体，T1487053微秒、peak1745/1760；共同141 T/peak保持、0丢失。48独立持出42→42、6仍未解，共同42 T/peak保持，没有持出新恢复。原59+新6共65条有witness未解，全部保留。

旧1229记录1170按预期通过、旧72全通过、新48的42通过，合计1349记录1284按预期通过（含1预期不可行拒绝与重复参数）；不可写成1284条可行图。979原记录与R44逐条name/pass/valid/T/peak全同，36/72/12资源同质，144外部最优审计/33证书。默认12/12 CTest实际通过（5.80秒功能墙时），20180priority、523numeric、2590shallow、495workspace独立金标涵盖实际默认源；与同SHA完整候选ClangUBSan结果对应，8条默认行为烟测5成功/3明确未解与完整候选完全一致。

同GCC15.2 Release/O3，baseline冻结R44默认EXE7861与候选Release3e827，原202全3轮CPU比1.104112/1.090299/1.134837、中位增加10.41%；新48全3轮CPU比1.075145/1.087209/1.093407、中位增加8.72%（独立side中位+8.09%）。全失败费用计入；不称加速。Host_busy/可用RAM每trial未测，用户后台仍活跃，授权前低RAM仅观察。研究/输入/output/profile与实际默认/实测EXE和flags分别冻结 `research/batch45/provenance.json`；默认源 `5116d8d9c859662a26d1aba7dd1b0916097cb2bd87e466007adf2cbede391dd9`、默认EXE `5accb1f112ad1bac31fcfeff8faf191ece90c64162d415ec95792721f9fd23a8`，实测EXE `3e8273e29d090a99f8224dad8e7a47cd6c5d313e50bee026e4064ed200cb02a9`。R44回退和旧R31报告保持，R46/R47负结果隔离，R48不混入默认。
