# R174：完整 336 图的固定 AWA* 候选覆盖计划（仅静态冻结）

本计划请求根代理审查后再执行一次；当前没有执行 336 求解、重跑旧基线或升默认。R172 源码、历史证据、原 v14/default 和所有旧 TeX 不修改。

## 输入与对照

- 唯一全集：`experiments/r107-age-portfolio-336/inputs.jsonl` 的原 336 条，顺序、族名、seed、原 JSON 和指令全部保持。
- 唯一初始 incumbent：同目录 `optimized_outputs.jsonl` 中 `age_portfolio` 记录及 `original_orders.jsonl` 的同 SHA/variant 见证；这正是 R109 冻结阶段已有结果，不是 R172 的更容易 84 图或重新调度结果。
- 原状态 272 verified、47 proven_infeasible_under_model、9 budget_exhausted、8 scheduling_failure 全保留。保留原 `report.json` 的完整错误/证书文本和后续独立证书的出处；后续可行性证据另列，不凭此新增输出或改写旧状态。
- 原 64 个缺少 incumbent 的输入仍占全集、失败/证书统计分母；本次只尝试改善现有完整合法输出，不伪装为恢复这 64 例。
- 所有 336 家族都进入报告。共享 DAG/寄存器 hazard 等不支持的输入也保留其合法原 incumbent，候选状态记 unsupported，不能删去后宣称达 Level。
- 静态原输入 matcher/eligible inventory 是筛选证据，不替代实际 incumbent 独立重放。

## 唯一算法与预算

直接使用 R172 的 `tree_pair_anytime.py` 和 `tree_pair_anytime_refine.py`，固定 w=2，累计每输入 20,000 个实际扩展/重扩展状态、总 search/emit 500ms、每 pair 至多 16 个 complete outlet、parent 子树至多 96 原节点。parse/scan/selection/restore/full emit/complete sink 处于同一绝对截止时间内。

同一个原 incumbent 决定全部 pairs 的 prefix、固定两侧 order、suffix 和排序；每个 pair 都从此 incumbent 开始，绝不把上一个 pair 的 gain 叠加。算法不增加 early COPY/再 GET/重算/别名/删除/重结合，不串行补旧 DP，不改权重/选择/剪枝/默认。所有实际完成的完整提案都保存，包括更差、相同、未胜出和中断前已完成者。partial/outlet limit/unknown 原样保留。

对 baseline 零 COPY 或没有 eligible pair 的合法输入只保留原输出并明确记 skip；不支持 matcher 只记候选 unsupported，绝不据此证明原 DAG 无解。输入 unsupported 检查可由 producer 明确记录已有 matcher 返回，但不引入新的求解策略。

## 验证与计时合同

正式执行前冻结 wrapper/core/producer、输入与所有初始输出/原 order/hash/资源参数，并对 272 个已有输出各做一次预检查：原 JSON 身份/每原一次/原有序操作数/真实物理窗口/RAW WAR WAW、独立符号与三个明确本地整数配置重放。预检查失败立即 fail closed，不给错误 incumbent 继续求解，不重跑 baseline 来补救。

每个新 complete 提案和最终 best 都执行同样四类检查，并保存完整原 order。校验不得使用调度器内部 state。原身份检查目的和整数语义检查目的分别记录；本地整数配置不冒称官方机器位宽。

candidate 搜索全部返回后才将该输入每个 pair 的稳定 immutable labels/OPEN/unfinished 原样逐行导出 JSONL，记录真实 i,j、全部 roles/ages、g/h、label version/共享 predecessor。每 pair 导出并释放引用，整个输入完成后不得让 references 进入下一输入。只保留 compact report 路径，禁止跨 336 堆内存。search/emit、wrapper stop-before-export、diagnostic materialization、JSON/I/O、独立 verification、全集 end-to-end wall 分别计时；500ms 仅 search/emit 截止，不承诺全流程 wall。

## 分母与结果

固定全 336 的状态/成功率、缺输出率、unsupported/skip/partial/outlet、完整提案数量逐族报告，始终列出 47 原身份模型证书及 17 原预算/启发式失败。对同一 272 原合法输入配对报告 COPY 总量、COPY/(N+COPY) 等权均值和 COPY/N 等权均值，以及每输入 before/after/增益/退化。候选 unsupported 仍以合法 incumbent 进入这 272 配对；不可把只匹配树的子集均值冒称全 272。

全 336 有 64 个缺合法输出，因此其已取得质量均值未定义，不能把其 COPY 置零。报告全 336 的分母覆盖和缺失明确；若另外列部分贡献，必须注明不是全量得分。官方 Level2、COPY 分母与平均权重仍未核实，严格模型/自生成图不证明官方 Level1/3 成败。R143 的必要界仍只是必要界，不是本次取得 COPY。

## 存储、成本与资源中断

R174 静态报告记录实际 F 盘剩余空间、原源文件大小、R172 480 complete outputs 和实际 JSONL 的总字节，并列出 input-only eligible 数与下面保守上限。不要以相同 500ms 假设相同提案/存储吞吐；预声明不做隔离性能因果结论。

每次实际状态扩展最多生成两个后继/目标，因此每输入完成提案数不超过 `min(40,000,16*eligible_pairs)`；所有被尝试 pair seed 标签加起来最多 eligible_pairs，因此 immutable labels 不超过 `40,000+eligible_pairs`。这些界包括 reopen 产生的新版本；stale 不扩展。父子树最多 96 节点，单条 label/path 的局部深度至多 95，所有真实活角色至多窗口 W。不同 pair 保存出口只能来自实际完整目标，不能导出后补搜。

完整提案仍含整个原 block，而非只保存小 parent。保存真实原 prefix 至多 baseline_rows，后续每原合法 deadline 发射最多 W-1 次 COPY，否则该发射 fail closed，故一个 complete 提案物理行数保守不超过 `baseline_rows+W*N`。静态报告以此算全集提案行上界；此界很松，明确不声称当前约 3.8GiB 空间能容纳最坏界。每行字符串大小与原 reg/id 内容有关，不凭行数宣称精确字节上限。

执行前估算：复制/链接来源证据清单和固定 source、原 input、272 baseline/final 大小，再用 R172 实际最大每输入诊断/提案字节作保守工程估算并预留至少 256MiB 的停止/记录空间。必要性数学界与工程估算分别标注。如果根代理认为剩余空间不足，不开始全量候选；不得删除用户文件或改为挑小图掩盖。

执行期间逐文件 stream 写入，保存完成文件后记录 hash/字节；在每输入前、complete sink 前、诊断导出前检查 reserve。空间不足/I/O 失败必须停止该次候选阶段，保存已完成证据/partial、保持 baseline，并将未执行输入明确记 resource_unknown，不删图、不压缩搜索范围、不改预算、不丢掉更差完成提案。资源 guard 属 producer 的失败保护，不得静默转换成“搜索证明”或填造旧时钟；若异常中断，原文件和错误单独保留。此 guard 的具体实现与字节 reserve 需根代理同本计划一起确认，当前尚未写入/运行新 producer。

一次候选理论搜索截止总和至多 eligible_inputs*0.5s；parse 在每输入截止内但 checker/JSON/诊断不在此界内，不能据此承诺全量实际 wall。无 GPU/付费依赖，单 Python 进程、逐输入处理。执行前记录实际空闲 RAM，RAM 不足则不启动；不关闭或干扰用户应用。

## ca93 回归范围

R173 从 R172 已保存完整 outputs/frontier 做静态归因。原 23 COPY、旧 DP21、AWA23 原样保留；parent62 耗尽自己的固定侧序提升搜索，parent61 第16个 complete outlet 中断；此时累计 7580 states、约149ms，未触发 20k/500ms。parent59 的旧21见证尚未被尝试。保留全部16提案成本、实际 OPEN/unfinished 和旧21 order 投影，不能说一般 DAG 最优、不能将当前 OPEN 的必要 floor 说成可达。计划不修排序/16出口，不通过串行补 DP 隐藏此回归。
