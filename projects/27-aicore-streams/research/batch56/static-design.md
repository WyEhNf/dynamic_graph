# R56 静态方向：一次因果输出延迟，而不是扩大内部 cut beam

当前仅设计；不实现、不编译、不调用求解器、不测试原63/67/250，不改变默认R51。

## 已执行且被冻结的负结果

R55 normal/UBSan原160金标、16 direct repair控制、160完整固定计划分别完成。原R52十二例whole4/12保持、八例仍失败；所有四个共同whole及helper计划/T/peak相同。原十二helper逻辑收费54,717,560→60,829,525（+6,111,965，+11.17%），不是wall/CPU性能测量。不推广；73文件总冻结见 `research/batch55/negative-checkpoint.json`。其内部order改变不能改变完整C的末态：done=D∪C；每个原DIRECT producer剩余用户数由集合决定；held身份及live同样由集合决定。较低cut peak不是较好后续身份状态。

## 实际失败归因（同R52十二，不外推63）

输入only加已保存真实前缀，逐BEGIN/END原边生命周期重算，见`external-release-static.json`。22份完整probe nofit终态，存在多个outside-global-ready-fit，但一个外部执行立刻让C-ready fit的数量是0。因此不为外部union盲加预算/128上限。八whole失败中，两个outer-prefix出现严格强制显存超容量；其余六未检出，既不是可续证明也不是图不可行证明。

* projection_retention_seed203451023：第57个从零计数的outer动作p=629842833；j=1570508042的必要同时持有界2469>2450。p终态原held rank13、完整remainingDIRECT闭集仅7节点。
* projection_retention_seed203451018：第42动作p=1348661544；j=1399095202的界1656>1547。p rank1、闭集6节点。

两p均在原top24、128以内，故改宽不解决这两个前缀。记录的单流原witness仅离线证明原输入有完整可行序列并观察最早分歧，不供算法读取、挑seed或制定名称规则。witness中j确早于p（34<95、24<65）。另两已恢复control的cut前缀也被这个必要界排除，但projection fallback已恢复其whole；不能误称whole不可行。

## 原DAG完整小反例与物理证明

全AIC1、hardware AIC1/AIV1/1 stream、event0、每节点exec1，deadline4，cap100。P0:W0/O30 root；Q1:W0/O50 root；J2:W50/O0输入Q；C3:W0/O0输入P,J。P输出须保留至C的END。R51 cut helper第一步以净输出30<50选P；剩余P闭集含Q,J,C；Q可BEGIN80，但J须同时持有P30+Q50+W50=130，不能完成。单步fallback执行Q后也仍无fit。

合法完整序列Q,J,P,C：BEGIN依次50/100/30/30，T4，peak100，C结束释放P。两个root及数据依赖完全相同，不是改图或重算。此小图whole默认可能由已有小图穷举恢复，反例只针对release_cut_order路径。12份手写完整原计划含wide130、equal100、zero、exactMAX、sink、external-DIRECT共享控制，独立Python bigint固定plan物理记录见`causal-deferral-manual-original.json`。没有求解新原图。

## 必要界与候选唯一变化

设D是原图合法物理prefix，j未完成。j开始时所有strict ancestors均完成。若producer p属于D或j的strict ancestors，且p有原DIRECT consumer c∈{j}∪Desc(j)，p.O必须仍持有。D里的sink也保留到全图T。去重累加这些原producer.O，再加j.W+j.O，得到B_j(D)；只作为必要界，不能用≤cap推出可行。原题Compute BEGIN同时分配W/O、结束只释放W、最后DIRECT后继END释放O，完全保留。不同pool核不合并，此诊断不声称T最优或并行排程不存在。

拟单一机制：在原release_cut_order的真实no-progress（非预算耗尽、非原成功）且2M收费尚有余量时，检查原未完成的j，不限当前ready。上述两实际阻塞target均尚未ready，ready-only检查会漏掉已经不可逆的更早阻塞。基于原边、实际prefix查B_j(D)>cap；沿已保存prefix寻找这个界第一次严格跨容量的原producer p，只接受p.O>0、有remaining原DIRECT user、位于原终态held top24、p和j原可达关系均不包含对方。选唯一确定性pair：按(first-cross-prefix-index,j原ID,p原ID)，不看名称/seed/任意witness。j的祖先强制持有构成固定基数；独立p一旦完成，存在consumer在j以后，直到j开始都不可能释放。因此第一次跨界确由这个原完成动作导致；p,j独立保证自愿j先于p不会造成原DAG环，但不保证整个新排程可行。

随后只从空状态重启一次原cut排序，暂不选择p直到j完成（包括single/safe/cut内每个BEGIN）。这是执行顺序约束，不新增数据依赖，不改变原users/degree/释放规则；cut仍是原producer的remainingDIRECT用户及原unfinished ancestors，128/top24不变。若某cut包括p但不包括j，该cut本轮可拒绝，原全局single/safe可以先推进j祖先。不得偷偷往closure加调度guard边、丢外部user或重定义输出寿命。所有完整结果仍由原独立event/core/memory/deadline模拟验证；失败明确返回没有被验证的可行计划。

原普通成功路径不变。新guard版与原版分离以避免成功普通路径因条件检查收费改变。检测、n/E访问、初始化、prefix扫描、reachability、top24排序比较、每次guard检查、复制、重启、结果合并收费均纳入同一2M；该2M与后续projection总16M共享。逐unfinished j通过原g.in/g.out显式DFS求ancestor/descendant，再扫描原producer/D/prefix；每次初始化、栈出入、edge visit及位比较均收费，没有免费的n²表或全图reachability预处理。必要界采用双uint64确切非负和（n≤4096时最多约2^75）或等价逐项剩余容量比较，不能saturate到MAX后误称fits。完整扫描不能付清就不给候选pair、更不重启；不能用未收费的partial最佳pair逃逸。只一次pair、一次restart，不增加seed、不叠R53/R55、无budget加宽；剩余不足立即止，不声称无解。保留独立completed/live身份，不能按同F合并。

## 待审的金标与执行范围

下一步若获实现授权，先预声明160原DAG/prefix控制：48小反例尺寸/ID/记录乱序/异构变体；32外部DIRECT用户、共享父、sink/零output和原依赖不可独立pair；32原拓扑constructed合法续排及distinct-identity controls；32 int64 exactMAX/aboveMAX、strict-vs-equal、top24 rank24/25、128/129 closure负控制；16独立手算收费临界。全部producer∈合法D、正O且有remaining原DIRECT users的资格逐项检查；不合法/不适用明确负控制。所有图有完整原节点固定计划金标，错误部分前缀不能冒充原图无解。literal费用由最终源码前静态表独立推导，不能按候选输出改预期。

先GCC/UBSan金标，再仅同original R52十二例对照全部helper/whole计划/T/P/收费/耗尽。新收费可能减少projection预算或丢失旧恢复，必须保留负结果。只有此小批有实质whole恢复才考虑请求63覆盖；无收益不能自动扩大。当前不授权任何以上新执行。

## 一手工作及模型界限（本轮重新访问）

* Jin等，*New Tools for Peak Memory Scheduling*，https://arxiv.org/html/2312.13526v1 。computation graph scratch/output及dominant profile接近本题；isolated子图接口与dominance前提不能省略，原文sink可释放，本文额外保留sink至T。不能把标量minimum peak/cut-F当整图续排的充分状态。
* Fradet/Girault/Honorat，IPDPS2025，*Parallel Scheduling of Task Graphs with Minimal Memory Requirements*，DOI10.1109/IPDPS64566.2025.00042；作者材料https://synchron-2025.imag.fr/slides/alain_girault_scheduling_2025.pdf 。合法顺序骨架可引导内存受限并行，但本题独立AIC/AIV、stream/event时延和deadline不在其保证之中。拟方向先改变合法顺序骨架，不声称继承最优/并行加速保证。
* Chen/Beck，CP2026，*Linear-Memory Beam Search Algorithms in Domain-Independent Dynamic Programming*，2026-07-13，https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2026.12 。其BSS/BULB讨论有限偏差回溯与存储/求解能力交换；本文只一个有物理原因的prefix顺序偏差，有限预算且不完整，不借用complete guarantee，不机械复演旧n≤512 beam。
* Zhou等，*A Learning Method with Gap-Aware Generation for Heterogeneous DAG Scheduling*，2026预印本https://arxiv.org/html/2603.23249v1 。提醒受限制生成过程丢失合法顺序空间，但没有本题持续输出/最后DIRECT END证明；不引入learning依赖或GPU。

当前预期仅两个已观测pre-cut阻塞有结构依据；不能由witness顺序或必要界推断可恢复率。检测成本、同预算余量及旧fallback损失是主要风险。静态报告与完整小图提供可审查机制，尚无算法改进成果。
