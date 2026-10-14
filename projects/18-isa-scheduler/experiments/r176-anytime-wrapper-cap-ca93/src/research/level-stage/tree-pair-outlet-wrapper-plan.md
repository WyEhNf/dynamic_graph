# R175：每 pair 出口上限的 wrapper 补充计划（尚未执行）

## 已核实问题与单一改动

R172 wrapper 在 `outcome != exhausted_improvement_search` 时直接 `break`。这把 core 的 `partial_outlet_limit`（本 pair 的16个完成出口上限）误当成整个输入的终止条件。16出口是每 pair 参数；500ms、累计20k是每输入预算。R173 的 ca93 只到第二 pair 就停止，7580 states/约149ms，故尚有总体预算却没有继续下一原 eligible pair。

只修改 `tree_pair_anytime_refine.py` 的结果分派/整体统计：

1. 收到每一个 child 返回，仍先累计真实 processed、保存该 child 完整统计与稳定 diagnostic 引用。
2. `partial_outlet_limit`：记录 capped parent，记整体“曾有未完成 pair”，继续原排序中的下一 eligible parent。
3. `exhausted_improvement_search`：照旧继续。
4. `partial_budget` 或其他非上述结果：照旧停止，不继续耗预算，不把 incomplete 当 exhausted。
5. 下一 pair 前照旧检查同一绝对 deadline 与累计 processed，不增加每输入预算，不重置时钟。仍向 child 传 `max_states-processed`、相同绝对 deadline 和16出口。
6. 若最终只出现 cap 而没有总预算终止，整体 outcome 保持 `partial_outlet_limit`，另存 `outlet_limited_parents`；若后来耗尽预算，整体 `partial_budget` 且仍保留 capped parents。不能在最后 exhausted child 后把整个输入标 complete。没有 cap 时已有 outcome 语义不变。

拟采用逻辑（仅设计文本，当前 wrapper 未修改）：

```python
child_outcome = result['stats']['outcome']
if child_outcome == 'partial_outlet_limit':
    outlet_limited_parents.append(parent)
    stop = 'partial_outlet_limit'
    continue
if child_outcome != 'exhausted_improvement_search':
    stop = child_outcome
    break
```

selector、core、g/h/cost、权重、safe prune、COPY策略、同一个初始 incumbent、不组合 gain、complete sink、每 pair16、总500ms/20k/parent96全部不变。只增加整体 cap 统计；其 JSON 编码属于 producer。保持原实际 R168/R170/R172/173/174 证据不变，不补旧时钟/前沿，不升默认，不串行 DP。

## 小范围验证合同（待根代理授权实施后实际执行）

先冻结实现、测试、输入 SHA 与生产参数，再运行一批独立 wrapper 控制边界测试和 ca93 一次真实候选。没有全336、84重跑或旧baseline重跑。

### 两 pair 控制边界

测试仅隔离 **wrapper 控制合同**，不宣称是真实 search 性能或质量收益。使用原 ca93 完整原 input/23 COPY baseline 和两个已保存完整合法 witnesses；mock child 调用，必要时 mock selector 的 forest inputs 但不修改生产 selector。更稳妥地保留真实 selector，在第1个真实 parent62 返回受限结果、第2个 parent61 返回合法21 COPY已保存 witness，随后用预算中断禁止进一步 mock 搜索。mock witness 不声称属于 parent62/61 候选族，明确只验证 wrapper 将完整 proposal 送入 sink/留存逻辑；真实 family 合法性由下一节真实 ca93 检验，二者分开。

- 第一 pair 返回 `partial_outlet_limit`，例如10 states、16出口记录、明确 synthetic sentinel；第二 pair sink 一份完整21 COPY witness，返回 `exhausted_improvement_search`。验证确实调用第二 pair、best21、所有 proposal/diagnostic 引用保留、整体 partial、capped parent 已记录。
- 保存对每次 child 的调用参数断言：对象 identity 是同一个 baseline；absolute_deadline完全相同；第二剩余状态是 `20000-10`；每pair max_outcomes16、parent96，没有把21作为新初始值。
- 重复用“第一cap、第二budget”检验停止且整体 budget，同时保留第一cap的 partial与完成结果。
- 第一cap真实累计用完 max_states，第二 child 不得调用；终态 budget；第一提案保留。
- 第一cap sink 后注入模拟到期时钟，第二 child 不得调用；终态 budget；注入时钟不是真实性能。
- 多个 cap 后最后 exhausted：整体仍 partial，全部 diagnostics和父编号留存，不称全局/固定族最优。
- 无 cap/全部 exhausted 的已有行为保持。mock queue/result必须明确 synthetic-only，不纳入真实求解成功率。

所有被 mock 送进 sink 的物理完整 witness 使用独立原身份/窗口/hazards、符号与三本地整数重放；synthetic stats/frontier 不冒称 raw age witness。若使用 sentinel，仅用于引用数量/生命周期测试，不写入实际 physical frontier 数据集。真实 export 验证只对下面真实 child snapshots 执行。

### ca93 一次真实原图

读取 R172 原保存 `ca93...-baseline-output.json`（23COPY）与原64节点输入，不重跑生成 baseline；预检查一次全部四验证。新 wrapper 调用未改 core，固定500ms、累计20k、每pair16、parent96、原 eligible排序、同initial。所有 actual complete保存完整output/order，包括更差；每 child全部 immutable labels/OPEN/unfinished流式保存，whole input search结束后export/del，export/JSONIO/verify单独计时。

报告：实际尝试父编号和全部子outcome/processed/firstgoal、累计值、多个cap、是否真的到达parent59、是否实际改善23、相对旧21只是对照而非fallback。即使仍没到parent59、没有提升、更多cap或发生总预算unknown，全部原样保存。实际 proposal需要原身份与符号/整数检查。不得把 wrapper mock 恢复21当真实 ca93结果；不得根据旧21提前直接选择parent59。若触发 correctness error则fail closed，不改matcher/goal/预算补救。

## R174存储策略的兼容性与变化

R174的数学界仍覆盖该修改：每输入累计扩展20k、每扩展至多2后继/目标、每pair16；complete≤min(40000,16*eligible)，immutable labels≤40000+eligible，所有partial出口保留。新 wrapper可能尝试更多pairs，实际JSONL/提案数量会高于原R172的一cap即停，故R174的454MB工程外推不能当修订版预测/保证。R174冻结文件不改；新阶段另列观察。

当前输入诊断仍只在同一 literal search返回后流式导出；逐pair释放、下输入不得持有引用。更多cap的 completed proposals仍sink到文件；wrapper不得积累所有完整输出，只保留best/当前child结果与稳定labels引用。每输入完成后释放当前child/diagnostics，compact report保留路径。resource reserve/文件字节/hash、I/O失败resource_unknown和全部336分母保留的方案依然必需。

先用本次 **单个真实ca93** 实际文件字节/labels/峰值观察审查 producer 合同，再请求全336授权；本次不运行336、不增加R174预算，不把更多stored outputs当时延提升。根代理批准后实现才生成新源码冻结与实际结果，当前仅静态计划。
