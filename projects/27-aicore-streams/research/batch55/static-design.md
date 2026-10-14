# R55 静态提案：失败释放闭集的两路续排

状态：**仅静态设计，等待父任务审阅。未写候选、未编译、未执行 solver/性能/默认推广。**

起点只能是 R51 的 `solution/solution.cpp`（8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b）。不叠加 R53/fcbb final-live 筛选，不叠加 observer。默认仍 145/202、42/48，剩余 57+6 个有 witness 的未解图；已有 witness 不进入候选的输入或选择规则。

## 为什么换顺序，而不继续做安全筛选

已保存的 R52 共 22 个 no-fit cut 快照，包含 14 个来自 whole-failed 图的快照。仅在最后一步换另一个当前可 fit 任务，0 个快照能保留下一步 fit。C 内后代必要持出界发现的 2 个早期不可逆 transition 都来自已恢复控制；补上原图外部 DIRECT consumer 的全图 reach 后发现 4 个，仍都来自已恢复控制。因此，不把这一必要界做成新的安全筛选候选。

另一个静态事实是：22 条已记录的 cut 执行路径在停滞之前都有真实 ready-and-fit 分叉，14/14 来自失败图的快照也如此。这里只说明 greedy 曾丢弃不同 completed-set 的选择，不证明任何替代分支能完成。快照每 reason 最多保留两条，不代表全部 cut 轨迹，也不代表剩余 63 图的全部搜索空间。

三个静态报告分别为 `saved-frontier-static.json`、`saved-fullreach-frontier-static.json`、`saved-cut-branching-static.json`。所有计算仅对已经保存的 prefix/order 做整数和原边查询，没有求新的大图完整计划。

## 完整原图反例

硬件 AIC=1、AIV=1、stream=1、memory=100、Wait/Record=0；所有节点 AIC、core=1、exec=1，deadline=5。节点行不是简化的 profile：

| 原始节点 | workspace | output | 原始直接前驱 |
|---|---:|---:|---|
| P=0 | 0 | 50 | 无 |
| A=1 | 0 | 20 | P |
| B=2 | 20 | 30 | P |
| C=3 | 50 | 0 | A |
| D=4 | 0 | 0 | B |

P 完成后，P 的完整 remaining-DIRECT-user ancestor 闭集正好是 `{A,B}`。C/D 是闭集之外的真实 DIRECT users，边和输出均保留。

当前 `(output-freed, workspace+output, original-id)` greedy 选 A：A 的净增加 20，比 B 的 30 小。P,A 后 live=70，B 的 BEGIN 需要 70+20+30=120；C 的 BEGIN 需要 70+50=120，二者都不 fit。此时 A 输出不能提前丢弃。

完整合法计划 `P,B,A,D,C` 的 Compute BEGIN 重叠依次为 **50,100,100,50,70**，T=5、peak=100。B,A 这条闭集次序先完成所有 P 的 DIRECT users，再释放 P 的 50；D/C 按原边完成后才释放 B/A。独立 Python bigint 重放的每个 BEGIN/END 和 held 输出身份存于 `manual-original-physics.json`。这是 cut-greedy 的反例，**不是 whole 默认程序失败的证据**（整图其它策略可能已找到此小图）。

更强的 identity 控制把 B 改为 W=40/O=20，把 C 的 W 改为60、cap改为110。P,A 与 P,B 的 live 都是70，但前者 B/C 都不 fit，后者可以 A,D,C，完整峰110。不能因为两状态 F/live 相等而合并；也不能因为前者已达到的 peak 更小就删去后者。

8 个人工全图 order 控制已静态 bigint 重放：5 合法、3 提供的计划预期非法。包含宽容量旧 greedy 可完成、cap 少1、两个 sink 的留存，以及 A 的两个外部 DIRECT consumers。没有以模板名称或这组 order 给生产算法提供选择答案。

## 唯一机制

保持 R51 原 greedy 完整运行；**只有一个已经构造完整 C 且未超128、greedy 因 ready-but-no-fit 返回时**，在同一个 prefix、同一个 C 上启动一次 width=2、branching=2 的紧缩状态 beam。原 greedy 成功的 cut 不重排；原 closure cap/输入资格/预算失败不触发 repair。

每层每状态扫描 C 内所有尚未完成、degree=0 且物理 fit 的节点。按原 greedy 三元组取前两项，不引入 workspace-first、future-bound、额外 pivot、额外 Event 或随机种子。每层最多四个 child，按 `(live,peak)` 严格升序保留两个，平局保持生成顺序。完成全部 C 后可返回真实合法的低 peak order；没有完整 order 就返回 invalid/exhausted，不能把 pruned 或 helper 成功称为 whole 可行。

去重只允许 **完全相同的 C completed-mask**（两个 uint64 覆盖128位），同 prefix 下其未来 users/degree/held identity 相同。相同 mask 保留较低 peak 的 state，peak 平局保留先生成者。不同 mask 即便 live/F/peak 相同也保留不同身份候选，再受 width 限制；这只是启发式宽度截断，不是 dominance 定理。

同 mask 的低 peak 保留只用于串行内存续排：剩余物理状态与 cut 的串行总时长相同。它不保证将来映射到多个 stream 的 T 更优；多流/Event 后的质量仍由完整候选模拟检验。

这复用现有 `beam_ordering` 的 ready 分支和 completed-set 去重概念，但不机械重跑已有 n<=512 整图 beam：新的起点是 R51 实际 prefix，范围是最多128节点的完整释放闭集，固定外部 held 输出和原 DIRECT users 继续影响每一个状态。R32/33 整图 backtracking 的0恢复负结果、当前整图 beam 的覆盖限制必须一并保留。局部两路也可能0恢复，不预设收益。

## 紧缩状态与原边不变量

U 是 `C ∪ 所有 C 节点的原始 DIRECT parents`。U 映射仅用于 state 存储，不改图。初始 U users 从 prefix 的全图 remaining-users 读取，包含全部外部消费者；C degree 从全图 prefix remaining-degree 读取。C ancestor-closed，未完成的前驱必在 C；新 child 只减 C 内 successor degree，外部 degree 无需用于局部就绪，但外部 user 绝不从 U users 中扣掉。

每 child BEGIN 检查 `memory_fits(cap,live,W,O)`，之后才做安全加法。END 加 O，减原始 DIRECT parent user，仅计数归零才减相应 O；C 的 sink output 与 prefix sink output 均留到 whole T。未涉及的 prefix held 输出仍包含在 initial_live，不能漏掉。对 U users 和 C degree 的紧缩复制保证物理身份正确；同 completed mask 的这些值是确定的。序列仍全部原始节点，返回后由原 `apply` 再检查原边/内存，最终实际候选独立事件模型核验。

不增加第三方依赖，最终仍 `problem.h + 标准库` 单文件。AIC/AIV、core 数量、exec、deadline 和 Wait/Record 语义不改；该局部串行次序本身只解决内存顺序，deadline 仍须由现有计划/模拟筛选判断。

## 收支与风险

全图 cut 预算仍2,000,000，cut+projection总预算仍16,000,000；C上界128、held top24、projection threshold/seeds不改。repair 的映射、边扫描、state复制、比较、去重、重建全部计费，详见 `charged-work-design.json`。预算检查发生在相应工作之前，不能先做无账操作再补账。不会给 repair 另开预算，也不会在预算用完后继续偷偷选择。

原 greedy success 的输出原样保留，但失败后的额外 work 会挤占其它 cut/projection，可能使原 whole 成功丢失，或使 budget 图更早耗尽。width/branching=2 又可能丢弃必须的第三条路径。这些是明确的验收风险，不能用小图可行性宣称真实恢复或通用加速。资源性能此阶段不测。

## 预声明验证门槛

计划控制分母 **160**，严格分族见 `gold-declaration.json`。所有图保持原始节点/边/hardware/deadline；标注 cut eligible/ineligible、128 cap skip 与 full plan valid/invalid 是不同字段。独立 bigint 重算 prefix D、原 DIRECT held set、每一 BEGIN/END、sink/T，并对小图枚举原 topological orders 作为 oracle；不同 mask 同F不得合并、同mask只保留低peak需单列。精确计费边界在执行 gold 之前冻结字面值和表，不能根据输出修改 expected。

父任务允许实施后，先冻结 isolated source/所有编译输入，再跑160 gold、适当 ClangUBSan/预算控制；之后只跑 R52 同12个原图 source-only before/after，保存全部完整原计划与失败 raw/charge。不因 helper 变好就声称 whole 恢复。未获后续明确授权不执行63/67/250/1099/性能/默认推广。若12没有真实恢复且原控制无新价值，记录负结果后请求是否停止；不得自动扩大width、branching、预算或 seed。

## 一手工作及本题边界

1. [Jin 等，New Tools for Peak Memory Scheduling](https://arxiv.org/html/2312.13526v1)，2023预印本。scratch/output computation-graph、one-shot 和 profile dominance 最贴近本题。线性化需要 isolated 子图和更强的 dominance，不能用最小 peak 或最终F替代。其原 sink 释放，与本题保留到T有差别；本提案不引用其 exact/FPT 保证，也不做图线性化。
2. [Fradet/Girault/Honorat，IPDPS2025](https://ieeexplore.ieee.org/document/11078551/)，[作者2025讲义](https://synchron-2025.imag.fr/slides/alain_girault_scheduling_2025.pdf)。可行串行次序可指导动态并行执行；这支持先找合法次序再交现有 stream/Event 模型，但不能把其并行可行保证移植到尚非最优串行解、本题 sink/core/Event 模型。
3. [Kulagina/Benoit/Meyerhenke，2025](https://arxiv.org/html/2503.22365v1)。HEFTM 纳入处理器内存并允许 eviction/adaptive 重排；本题共享内存、禁丢弃/换页、固定参数，不能用 eviction 修复死锁。此处只借鉴生命周期的重要性。
4. [Zhou等，2026 gap-aware DAG scheduling](https://arxiv.org/html/2603.23249v1)。受限生成顺序会排除可行序列，是审视 greedy order-space 的相关证据；它不证明持久输出的内存可行性，不引入其学习器。
5. [Chen/Beck，CP2026 Linear-Memory Beam Search](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2026.12)，出版2026-07-13。讨论有限存储下完整 beam/backtracking 的代价与质量取舍。本提案只有 width2 的不完整局部 beam，不采用完整/最优性宣称；该文也不提供本题恢复率保证。
6. [Bathie/Marchal/Robert/Thibault，2020](https://icl.utk.edu/files/publications/2020/icl-utk-1383-2020.pdf)。强调只看当前 ready 可能最终碰到 memory wall，以及处理器限制会改变峰值模型。本题不直接采用其改边算法；本提案不增加/删除原依赖。

上述文献不等于收益证据。当前只有完整原DAG小反例和已存前缀更早存在分叉的证据；真实收益仍未知。
