# R53静态设计：固定前缀与完整闭集的精确最终live支配筛选

仅从默认R51的8b7c单文件开始；R52是观察器证据，不进入提交。只加一个筛选：已有合法incumbent cut时，新的完整closure的精确最终live严格大于该incumbent的final_live，才跳过该候选的greedy。相等必须继续计算peak，第一候选/尚无合法incumbent时不得筛选。保持2M cut /16M总预算、128节点/top24 producer/旧threshold/种子/原DIRECT边与释放时机。不加入rollback、扩大闭集、no-net筛选或新排序。

## 严格前提与公式

D是当前真实Compute完成前缀，degree/users/live满足R52独立审阅的状态方程。C是某已完成producer全部未完成原DIRECT用户及其全部未完成原祖先的闭集，C与D不交。闭集完整，所有C内原节点均会恰执行一次；对超过128而截断的closure不能应用公式作筛选，仍按旧规则拒绝整个可选cut。新的greedy尚未运行，公式不预测或假定候选可行。

令S=D∪C，H(S)为S中“原sink或至少有一个原DIRECT用户不在S”的节点。任何拓扑合法且容量可行的C执行次序完成后，清理workspace而未执行全图sink terminal清理时：

`F(D,C) = sum(output[v] for v in H(S))`。

证明：所有v∈S均已Compute完成，workspace均释放。非sink输出恰在其最后原DIRECT用户Compute END释放，故仅当存在用户不在S时仍持有；sink在全图T保留，其输出仍纳入terminal清理前记账。集合判定只使用D、C和原DIRECT边，不含内部次序。若S恰好等于全图，F是现有release_cut_probe的终端sink清理前final_live；峰值及后续greedy选择并不依赖最终清理之后的零值。不能把该F当作T之后的实际分配。

等价的局部计算：

`F = live - R + A`，

R只包括D中所有剩余原DIRECT用户都位于C的生产者输出，按distinct producer计一次；A只包括C中原sink或存在未完成cut外原DIRECT用户的节点输出。C中内部输出若被所有用户消费，不能累计到A；D中有任何未完成cut外用户的输出不能计入R。多个C节点共享producer不能重复减。原sink从不在R。

## 筛选安全性和预算边界

假设合法incumbent I已真实完成greedy验证，评分为(F_I, peak_I)。若精确F_C>F_I，则C即使合法，也在字典序第一项上严格劣于I；若C非法，本来就不可能成为选择。删除这一候选的greedy不改变完整枚举中真实合法最优cut。F_C=F_I的候选可能有更低peak，必须保留；相同F与peak仍按原先首次tie保留规则。F_C<F_I必须保留，即使内部greedy随后失败。无合法I时一律走原greedy，不能根据虚拟阈值、无净回收或未来可能incumbent提前筛选。

证明只针对同一前缀的完整候选比较。新bound本身计费，会改变固定预算下的停止位置，因此不能承诺原2M预算每条结果都不变或所有原成功自动保持。必须保留真实预算耗尽作为结果，不能退款、把新计算排除计费或提高2M/16M。若新计算代价大于节省，候选应被拒绝而不是推广。

这里的安全不等于greedy能找出每个闭集的所有合法次序，也不等于全图最优调度。严格劣于已验证合法I的闭集，其任意合法内部次序均具有同一个较劣F，因而不可能成为同前缀的更优cut；未被删闭集仍可能因为原greedy局限而失败。incumbent只能来自本次前缀中`candidate.valid==true`的原实际greedy结果，不能由独立oracle的更佳内部次序或未来其他前缀的plan导入运行时。外层推进前缀之后必须丢弃旧incumbent。

## 预计修改点（未实施）

1. `release_cut_probe`增加可选合法incumbent-final参数；没有incumbent时不计算新F。只由`release_cut_order`当前真实合法selected传入其final_live，原producer排序/候选序不改。
2. 在closure完整且<=128、pending原topo列表建好之后、greedy之前计算F。>128旧拒绝路径先发生，不能以公式让129变成128或partialcut。
3. 计算R时扫描pending的原inputs，计数已完成parent在C内的未完成DIRECT用户命中次数；命中数等于当前remaining_users才释放。使用独立长度n的计数数组和distinct列表，不能修改done/users/degree/included，也不能复用同一个parent输出多次。
4. 计算A时扫描pending节点及其原out，判断sink或第一个尚未完成且不在included的用户。只读取原边；每新节点、边、计数/比较/累加和n个计数零初始化均按明确单位计费，budget失败按原失败机制返回，不能绕过预算。
5. 将live减R保持在非负int64范围（R是现有物理live子集），再以现有双uint64 `ProfileInteger`精确加A。每输入O非负int64、n<=4096，总和<4096·2^63<2^75，128位足够；不得以饱和MAX当精确F，不得将wide.lo有符号强转再比较。用`ProfileInteger(incumbent_final) < F`实现strict比较；hi!=0或lo>INT64_MAX也必须正确表示。
6. dominated返回的是“此可选候选不可能胜过现有合法cut”，不是图不可行或伪造合法plan。不得让invalid/pruned candidate设置valid。保留实际greedy完成后的final_live，并在测试中与独立F完全一致。提交仍单文件problem.h+标准库；观察器记录与纯公式参考函数只放local harness。

## 预声明金标与验收

`research/batch53/gold-declaration.json`先冻结完整原DAG模板/固定前缀/真实incumbent来源、边界与期望筛选条件。独立Python参考采用完整H(D∪C)集合公式；候选预计使用局部R/A计数，因此避免同一实现互相印证。所有物理结果另按全原节点BEGIN W+O、最后DIRECT END及sink到T的bigint过程重放；n<=8枚举全部原拓扑序验证cut合法最优比较，128/129不做阶乘枚举而只使用完整指定plan与严格集合公式。

拟覆盖至少160个静态公式/比较控制：手工模板族、固定随机种子的合法D前缀与真实祖先闭集，以及128/129边界。独立测试不从witness或旧失败顺序构造solver建议。模板含外部用户、共享parent、cut内输出外部user、旧/新sink、零W/O、MAX恰好/超过MAX/超过uint64、first-no-incumbent、合法/非法竞争者、equal-final-better-peak和完全tie；全图必须包含所有原节点，capacity/deadline不改。

后续执行顺序（需父任务CPU授权）：先独立集合/局部公式/完整物理gold；再隔离单改源码与小budget控制，保留R52同12图并比较所有原成功与真实计费；只有安全控制通过才诊断原57+新6失败及4旧恢复（非性能）。若无新增真实恢复且无充分成本收益，保留负结果，不直接full/performance/default。任何新增恢复必须冻结原硬件/节点/deadline、实际完整plan并独立heap重放，才申请完整1099/625/14CTest及202+48成本gate。

金标数量预定176：8手工竞争/相等/无incumbent控制、24外部用户与sink控制、16交叉依赖与零值控制、24整数极限控制、8闭集128/129控制、64固定种子小DAG控制、32计费边界控制。每个控制保存完整原节点/硬件/deadline/固定合法D前缀、全部候选闭集及真实合法incumbent来源；不满足预声明前提的随机样本必须显式报告并停止gate，不能删去后降低分母。随机模板从输入产生图，参考顺序仅作测试证书，不给生产选择器输入。每个预算控制的精确charged-work期望以随后冻结的逐操作计费表为准，不以运行后的实际数字反填期望。

变更范围拟为`solution.cpp`中`release_cut_probe`参数与完整pending后的一段只读筛选，以及`release_cut_order`现有have/selected传参。不移动或删原4n复制收费、不提前修改外层状态、不改候选排序/score/tie。独立候选与测试将另存`research/batch53`；默认源码只有后续完整验收和父任务明确推广后才允许替换。当前设计固定参考源码位置：`ProfileInteger`第555行、probe第746行、outer第789行（行号仅对应冻结R51字节）。

当前仅静态设计和金标预声明，未编译、执行gold、调用solver或改默认/旧TeX。19唯一性能窗期间保持静态。
