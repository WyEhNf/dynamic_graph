# R44 候选：浅层消费者排列与真实可行性恢复

当前已晋升默认 R44，保留 R43 冻结回退；同 Release 成本配对和默认验收均已实际完成。旧 R31 报告、R39/R42/R43 冻结均保留。

实际落盘单文件源码 SHA-256：`d88860f2da7eb9b18d0271abec308a2aa1e6f426742eeecd01d58d87fd7034a3`。
功能验证 EXE：`997f29db14b9987c83bc0fe2411fce3f904fa9bfdd31cf5b267c9ceffb2cc4f6`，GCC15.2 `-O2`。
`solution.cpp` 已内嵌研究片段，并非引用外部 `.inc` 的提交包装器；提交依赖仍只有 `problem.h` 和标准库。
准备脚本曾打印 LF 内存字符串的 SHA，而 Windows 落盘为 CRLF。功能结果始终保存真实 `read_bytes` SHA；消息中的 `1dd982...` 已纠正，脚本已改用真实文件字节。

## 结构与模型

仅原始节点/边触发识别：可选独立前缀根、独立生产者、消费者反链、可选只依赖消费者的终端 sink。支持 `n<=4096`、消费者 `<=512`。不读题目名称、生成元数据、成功 witness 或其顺序。原始 63 未解记录中初步浅层分类有26条，受消费者上限与层选择影响，当前实际候选识别20条；其余图不扩大旧搜索预算。

固定消费者排列时，尚未执行的输入生产者在首次消费前执行。每次 Compute BEGIN 同时计入 workspace 和本节点 output；END 释放 workspace，原生产者 output 到最后一个直接消费者 END 才释放。sink 保留到全图完成。诊断剖面完全使用这些直接边，不消除传递冗余边。

独立生产者组内的工作区降序有条件交换论证。若组内的既有输入输出存活恒定、两个生产者的输出均持有到随后的消费者，则对于 `Wa>=Wb`：

`max(Oa+Wa, Oa+Ob+Wb) <= Oa+Ob+Wa <= max(Ob+Wb, Ob+Oa+Wa)`。

不同非零前缀输出可能在组内提前释放，这时论证不成立。实现检查所有前缀的 remaining direct users：只有前缀在全组后继续存活或由全组共同消费才重排，否则保留原输入顺序。独立负控制证明无条件工作区排序可以增加峰值；不会把这个反例归咎于题面模型。

消费者种子新增共享实际 producer 的输出加权邻近序列。高 fanout 的权重被度数归一化，评分配对最多100万、单producer fanout大于64时跳过评分，原依赖仍全部参与生命周期计算。局部移动延后造成关键割的消费者，或提前持有 producer 的最后消费者；也有有限确定性插入扰动。所有种子先统一评分，再给两个较好种子局部预算，避免第一差种子耗尽预算。

排列诊断可能超过 int64，即使存在可行遍历，因此使用标准库实现的双 `uint64_t` 精确非负计数，允许精确释放并比较 `(超容量面积,峰值,逐节点面积)`。`n<=4096` 下瞬时量小于 `2^76`，逐节点累计小于 `2^88`，双字不会溢出。面积按节点剖面计，属于搜索评分，不是物理时间积分。实际提交计划仍交原 R42 修复后的准确 Event/资源模型验证，诊断饱和分数不决定是否合法。

12M charged work 包含配对/邻近评分与剖面节点及边扫描；传统 bundle/memory 种子生成、排序和容器操作另有成本，所以这是搜索计数预算，不是整个算法的严格指令或 wall 上界。恢复分支仅在原 R43 全部候选失败后触发，不替换此前找到的方案。

## 已执行证据

初版顺序及首种子耗尽策略0恢复、排序初态策略0恢复均保留，见 `shallow-failed-first-seed-batch44.json`、`shallow-failed-ranked-seeds-batch44.json`。共享producer邻近种子首次恢复2记录，见 `shallow-failed-affinity-pre-guard-batch44.json`；对应实际源码/EXE单独归档，随后补上前缀条件与评分预算。

2590个独立 Python 任意精度剖面金标，覆盖多前缀、变化存活、累计大于 MAX 的诊断值和容量判定，全部 Clang UBSan 通过；另160个有界搜索有效性检查、756个恒存活交换枚举及变化前缀负控制通过。没有将搜索未返回计划当作不可行证明。见 `shallow-profile-ubsan-batch44.txt` 与 `shallow-gold-generation-batch44.json`。

R42 的523固定计划数值金标在真实 R44 源 UBSan 重跑全通过（11/320/160/32），无运行 UB 诊断。32近 MAX 缩放串行 witness 始终按固定计划正确验证；启发式是否求得另行统计，不用全图历史输出总和过度拒绝。

979历史回归全部通过、无 T 或等 T 峰值退化；执行56.462秒是共享 CPU 的单次功能运行，不是加速比。132外部最优审计及21证书通过；12强资源界另12/12精确通过，合计144最优审计/33证书；默认原10加新profile共11/11通过。

完整功能批：原202困难139→141，旧139的 T/peak全同；36结构36→36全同；72新种子持出68→72，旧68 T/peak全同。0丢失、0共同质量退化、0模型分歧。原困难仍61有witness未解。2原记录来自同一拓扑的不同内存参数；另4为新的独立种子图，不把两原记录说成两种独立结构。

新72采用独立 Python 生成并精确计算可行串行 witness，再打乱 sparse ID/节点记录；包含不同规模、producer W/O、消费者输出保留、多前缀、多sink、区间与非局部使用、0与大 Event。witness 只由测试适配器验证，算法不会接收它。

父任务独立 heap-event Python模型实际重放全部249份候选 passing plans（141+36+72），含8stream跨流事件；每个 T/peak/deadline精确一致，243共同记录 T/peak同旧版。原恢复的最终候选是8stream `T=3581299us`，不同于早期串行诊断 `T=3779533us`。独立证据在根 `outputs/stage2-root-functional-plans-r44.json`；旧诊断证据仍保留于根 `stage2-root-shallow-recovery-r44.json`。

所有功能比较明确旧默认 `-O3` 与新诊断 `-O2`，不比较它们的运行速度。同 Release 成本三轮已完成：202每pair CPU均增加，逐pair中位+9.19%，两侧中位+4.49%；共同61失败也计入。以恢复6记录为推广依据，不称整体加速。

## 复现入口与限界

`scripts/prepare_batch44.py` 生成完全展开的单文件；`make_shallow_gold_batch44.py`、`make_shallow_holdout_batch44.py` 生成独立金标和持出图；`validate_batch44.py` 执行202/36/72功能对照；`regress_current.py --label batch44 --bench research/batch44/aicore_bench.exe --source research/batch44/solution.cpp` 执行历史回归。

`reports/functional-summary-batch44.json` 保留每个输入、EXE及真实源码字节SHA，所有 before/after 原始JSON与CSV仍存在；成功计划可独立重放。默认 R44 已真实冻结，所有compile输入、默认与测量EXE分别有SHA，不覆盖任何先前费用数字。截止优先再最小T/峰值的提交排序、原始Event/生命周期约束保持；无可行候选仍显式失败。自建图与本地JSON适配器不代表官方隐藏测试，也没有官方测试包、平台算力时限或内存上限的实测依据。


第44批当前默认：输入-only浅层共享producer/consumer恢复分支，仅原R43全失败后触发，不读witness/名字。原202困难139→141，2条来自同一拓扑的内存参数变体；72新种子持出68→72，4个未见种子恢复；共同243 T/peak全同、0丢失/分歧。旧1229记录1168按预期通过，加72新图共1301/1240按预期通过（含1预期不可行拒绝），仍61条有witness未解。原36结构、979直接R43逐记录全部同T/peak。

多个prefix的真实输出存活逐原始DIRECT边计算，生产者W降序只在已有prefix存活恒定的组启用，变化prefix反例保留；标准库双64位诊断剖面避免超MAX后释放失真，实际计划仍由独立Event模拟器验证。2590独立Python-bigint剖面/160搜索有效性、756恒live交换/变化prefix负控制、523 UBSan数值计划通过；144最优审计/33证书、默认原10测试+新剖面测试共11/11（2.64秒）及20180priority金标通过。

同GCC15.2 Release O3/DNDEBUG原202三轮CPU比1.158333/1.091912/1.021567，逐pair中位增加9.19%；两侧中位21.250→22.203125秒为增加4.49%，不称整体加速。共同61失败CPU分别中位13.812500→15.359375秒；全部求解wall21.983504→22.445947秒、CLI22.998508→23.390441秒。新72的CPU比0.979730/0.942308/0.965986不能外推困难集。全部失败与恢复组费用见 `reports/resource-cost-summary-batch44.json`；root独立heap Event重放249合法计划已通过，早期pre-guard串行计划与最终8stream方案分别保留。

单文件源 `d88860f2da7eb9b18d0271abec308a2aa1e6f426742eeecd01d58d87fd7034a3`，实际默认EXE `7861a413437c0617705fffa335e6dbedead3cb3b15c5fff5ae25f3fef1920f56`，性能测量EXE `8d43bf1ff55eb0486d902652782b04c35fe32c7985eb5207e07fdffdbb507e16`，两者来源与所有compile输入SHA分别冻结 `research/batch44/provenance.json`。R43冻结留作回退，旧R31报告保持，最新续研报告更新；prepare曾打印LF文本SHA，已改实际字节，功能证据一直采用actual read_bytes SHA。恢复搜索增加CPU换取可行性覆盖；继续针对61条未解结构探索，不声称官方全图保证/隐藏成绩/主办方资源时限。
