# 2026-10-11 续研：模型迁移边界与首批选择

旧 R31 源码、TeX、PDF、基准记录保持冻结。当前参照为 202 个困难记录中 133 合法、69 个具有独立 witness 但尚未求解的记录。以下方案不读取 witness，不按测试名称或生成族分支。

## 原始来源

* Fradet、Girault、Honorat，IPDPS 2025，*Parallel Scheduling of Task Graphs with Minimal Memory Requirements*，DOI 10.1109/IPDPS64566.2025.00042。[作者发表记录](https://pop-art.inrialpes.fr/people/fradet/publications.html)、[作者 2025 讲义](https://synchron-2025.imag.fr/slides/alain_girault_scheduling_2025.pdf)。该工作从序列内存顺序构造动态并行 list scheduling，并检查剩余序列的内存预算。讲义给出图归约和分支界定，并公布 [MASTAG 作者源码](https://gitlab.inria.fr/spades-pub/mastag)；本次访问源码站点被 Anubis 拒绝，未把它记为已运行或复现。其保证属于论文的任务峰值/净影响模型；本题生产者共享持出、消费者结束释放与 Event 执行顺序需要独立推导，不能直接继承。
* Kulagina、Benoit、Meyerhenke，CCGrid 2025，*Memory-aware Adaptive Scheduling…*，[原论文 arXiv:2503.22365v1](https://arxiv.org/html/2503.22365v1)。论文包含处理器局部内存、边文件、通信缓冲和驱逐/重算。可借鉴内存优先级和插入时刻检查；赛题禁止改变数据生命周期，不能驱逐输出，也不能以消费者开始时刻代替结束时刻释放。作者代码/实验资料见文内 Zenodo 链接。
* Zhou 等，2026，*A Learning Method with Gap-Aware Generation for Heterogeneous DAG Scheduling*，[arXiv:2603.23249v1](https://arxiv.org/html/2603.23249v1)。主动 skip 能在有 ready 任务时等待下次完成，扩展工作保守 list scheduling 的可达顺序。这里可探索用额外 Event 实现等待；论文最优覆盖论证不含本题输出持有、固定流顺序和 Event 成本，不能宣称覆盖赛题最优。其 Appendix F 删除传递冗余边的做法也不能照搬：赛题直接消费者决定释放和显式同步，必须保留原边。当前先用 CPU 搜索，不引入学习模型。
* [Google OR-Tools 官方 RCPSP CP-SAT 例程](https://raw.githubusercontent.com/google/or-tools/stable/examples/python/rcpsp_sat.py)使用 interval、precedence 和 cumulative 资源约束。[官方 job-shop 文档](https://developers.google.com/optimization/scheduling/job_shop)说明区间与不重叠约束。外部 oracle 可为 workspace 建立 Compute 区间，为 output 建立从 Compute 开始到最后直接后继 Compute 结束的区间，sink 延续到 T。仅建 Compute 的常规 RCPSP 会漏掉持出内存，且任意开始时间解未必可由本题 eager stream/Event 执行器实现；须另外约束流和同步或把它只当松弛下界。第三方库不进入提交源码。

经典 HEFT、serial/parallel schedule-generation、memory-aware DAG 文献仍见冻结 R31 报告。续研的新论文没有与本题完全相同的模型；下面是本地推导与实验计划。

## 首批：有界序列前沿搜索

旧宽度 8/32 beam 丢弃前缀，固定 sink-closure 投影也只覆盖一组闭包内部顺序。完成集合决定原图的 ready 集、剩余直接消费者计数和持出内存，因此可用完整完成 bitset 记忆已经完全探索而失败的状态。先做串行内存可行搜索，再交给原独立 Event 模拟器过滤串行/并行候选。搜索预算耗尽不等于不可行；不写失败证明。

**可行性保持的归约（不是最小 peak 保证）**：若 ready 任务 A 的 workspace+output 分配可放入当前内存，且 A.output 不大于本次完成 A 将释放的父输出总和，则可提前完成 A。被释放的父输出都只剩 A 一个未完成直接消费者；它们在任何尚未执行 A 的后续前缀中一直存在，且其他任务不会使用它们。把这些独占父输出替换为不大的 A.output 不增加后续内存，提前满足 A 的后继依赖也不妨碍原可行顺序。A 的 workspace 已通过当前分配检查。因此如果存在串行内存可行完成顺序，就存在以 A 开头的完成顺序。早执行 A 可能增加已知最小 peak，故只用它搜索固定预算下的可行性，不作为 peak 最优归约。

**必要剪枝**：已完成 sink 输出将持续到全图结束。任一未完成任务启动时必须同时持有其 workspace、自身 output 和全部直接父 output。这组与已完成 sink 不相交；两者相加超过容量则状态不能串行完成。所有和使用 int64 饱和加法，不能把不同时间存活对象合成互斥关系。

首批只在 R31 全部候选失败后触发，限定中小图与确定性工作预算。小图用独立全子集 DP 核对可行性，返回顺序另由独立事件模型核验。以恢复数量、共同合法案例 T/peak、包含失败的求解 wall/thread CPU 分别报告，不把无解/超预算结果的 T=0 当加速。

## 首批负结果与第二批推导

R32 的 640 项检查通过，但完整 69 旧失败中 0 恢复；51 个适用规模图均耗尽预算，不能证明不可行。实验已冻结在 research/batch32，默认恢复 R31，未为了增加通过率修改任何测试输入。

第二批补充未来持出必要界：若已完成生产者 p 的某个直接消费者 c 等于未完成节点 i，或 c 是 i 的后代，则 p.output 在 i.Compute 期间必然仍活着。对所有这种已完成 p 的输出求和，再加 i.workspace+i.output、尚未完成的直接父输出、已完成 sink 输出，就得到 i 启动时必有的共存显存。已完成直接父输出已经包含在持出集合中，必须去重。已结束且已释放的 p 不会对未完成 i 满足该关系，否则 i 作为消费者祖先不可能仍未完成。这个界基于原图祖先关系，不产生 Event，也不改变释放规则。它有望较早拒绝导致将来消费者必然超显存的源节点组合，从而减少大量前沿回溯。该推导是本地方法，尚未验证收益，默认保持旧版本。

外部 CP-SAT 使用串行位置 interval 模型，不使用样例 witness 作为 hint。40 个任意小 DAG 的全部 3886 个拓扑顺序，按真实 64 位时刻的独立持出区间与单位位置模型峰值一致；记录见 reports/serial-slot-math-batch33.json。是否求到新方案仍须独立 Event 模型检查。

R33 的必要界通过 99781 前缀/未来节点检查和 640 项 DP/Event 检查，但原 69 失败仍 0 恢复，未推广。CP-SAT 则通过 96 个任意小图的独立子集最小 peak 判定；原失败中全部 13 个 n<=200 的记录各用 5 秒/单 worker 均 UNKNOWN，另外 56 个按明确诊断范围排除，仍完整保留压力集，没有不可行证明。

R34 改为优先尝试完成任何内存收缩消费者的祖先闭包（沿原始 DAG 拓扑顺序），按真实最终 live/过程 peak 排序，闭包不合适或所有宏失败后仍保留原单节点分支。这样把搜索从大量独立 producer 的开辟决策集中到消费者释放决策，但不宣称固定闭包顺序覆盖所有可行安排。原 69 失败恢复 3 个：535、341、146 节点。全部内部/独立 Event 指标相同且满足 deadline，640 项小图对照通过。保存代码和二进制于 research/batch34。单次运行成本只有功能性含失败证据，不与非同期 R31 计时直接比较；完整回归和配对尚待后续批次一起进行，默认仍冻结 R31。

R35 的消费者对闭包增加547节点恢复，R36贪心生产路径保留4个恢复。R36现已完整验证并冻结默认：202困难三轮均137合法/65未解、共同133的T/peak保持；全CPU中位+9.74%，不称加速。979严格、144标尺/33证书、CTest5/5及单文件编译均通过。历史段落的“尚待验证/默认R31”仅描述当时阶段。

## Dominance与结构分解的模型边界

[Jin、Purohit、Svitkina、Vee、Wang，New Tools for Peak Memory Scheduling](https://arxiv.org/html/2312.13526v1)的 computation graph 模型允许 output 与 scratch，接近我们的串行显存递推。但原模型在sink结束后释放sink输出；诊断需添加连接所有sink的零权重虚拟terminal，映射回原任务时删除terminal，题面不能提交exec=0的虚构算子。其 isolated 子图线性化依赖完整内存曲线的 dominance，单纯最小peak不够；外部producer/consumer路径必须通过规定边界，node-sum与computation graph隔离定义也不同。原始直接消费边不能随意删改。论文证明树/pumpkin的一般权重问题也强NP难；低outdegree的SP图参数算法并不说明一般大图容易。

R37隔离研究在宏的每次分配前执行当前能放入且净output影响非正的ready任务，包括闭包外任务。它应用上面的固定容量交换证明，所有实际执行节点一并回滚，保留原始生命周期；不同宏间实际执行序列可能不同，不能只算闭包名义节点。640项独立subsetDP/Event/预算检查已通过；诊断出现70节点新恢复，完整提交模型验证仍进行中。默认仍R36。

R37–R39统一验证现已完成，默认冻结R39。宏内归约恢复70节点；严格整图嵌套fork/join的两种完整子块顺序真实workspace/output profile候选恢复766节点，边界全部检查并保留fork直接到join边，不宣称任意交叠最优或dominance。新36结构图（独立随机DFS witness，非候选递推）14→36，原202为137→139，共同成功T/peak保持。1120前沿检查、39结构正/负检查、12额外subset最小peak、979严格、144标尺/33证书、CTest5/5与单文件编译通过。三轮旧202CPU+3.14%，新36CPU-11.30%（减少失败搜索），两种分母分别记录，不外推通用加速。旧历史段落的“进行中”仅描述当时阶段。

R40下一隔离路径准备将贪心阶段的全部候选向量改为稳定保留唯一最佳宏，并用完成bitset去重。排序严格优先(final_live,peak)，平局保留最早宏，所有宏仍按原先顺序评估，理论上原<=768的路径与搜索工作完全保持；将用直接双实现比较核对。另仅在旧方法失败的769..2048图尝试单消费者宏/宏内归约，不构建大fanout平方亲和对；仍8M搜索工作预算。预处理、排序/undo不完全计入该工作计数，不能把8M叫CPU时限或保证所有大图有解。当前未编译/未测试/未推广，等待共享CPU窗口释放。

R40现已完成功能诊断并冻结负结果，不推广。1120独立检查、332条双实现贪心路径/工作/中止状态逐项相同，但新增大图范围没有恢复原69中的任何更多记录，仍6合法/63未解。1000独立sink的可行研究输入验证384层保护，在931392工作时明确策略中止、失败状态0，避免扩规模后原生栈失控。单次成本仅作为含失败的功能证据，不声称性能。默认R39保持；存储优化和结构emit可另作独立成本批，大图增加搜索不能因有界就普遍保留。
