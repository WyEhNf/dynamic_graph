# R167 静态方案：单一固定权重 Anytime Weighted A*，待审阅

2026-10-11。这里只冻结研究方案，没有执行新求解器、oracle或84批。
原auto、全336/72、R164证据及全部旧报告不变。下一次实施/功能执行需root协调并审阅。

## 冻结证据和明确缺口

R164固定84：65合法/19原限定模型证书，COPY11491→11487，仅3图改善4COPY。
10completed、43partial、31不尝试。R166逐实际记录发现：42 state-budget中**41首pair、1第三pair**，另1首pair时间预算。
最后失败pair全部0出口；其中一个输入前两pair已有完整出口。不可把“最后pair0出口”写成“43输入全无出口”。

R166只读取原JSON和实际保存order，提供side lengths、进入时external ages、每个prefix的结构live数；
**不是实际unfinished年龄frontier**。旧producer未记录终止progress/frontier/role ages，不能事后补造。
所有state耗尽窗口为W8/16/32，除了一个后续pair W4；最小首pair为两侧15/15，其余多为31/31或偏斜15/75。
原balanced64/W8首pair31/31、无external，已实际处理20k且0出口；该完整输入不缩小、不换种子。

代码的可证明访问障碍：旧DP必须遍历完整progress层再进入下一层，所有局部原节点层完成之后才处理parent与全block恢复。
因此即使某条具体合并路径可继续，尚未扫完浅层就不能发出它。状态膨胀是否主要由哪类role ages造成仍未实测；
这轮只改访问顺序，不猜测安全年龄支配、外部对称或增加预算。

## Primary研究依据

Eric A. Hansen, Rong Zhou, *Anytime Heuristic Search*, JAIR28 (2007),267–297,
DOI[10.1613/jair.2096](https://doi.org/10.1613/jair.2096)。
[作者预印本完整原文](https://arxiv.org/pdf/1110.2737)，
[AAAI出版社PDF](https://www.ed.aaai.org/Papers/JAIR/Vol28/JAIR-2808.pdf)，
[出版社目录](https://ocs.aaai.org/Press/Journals/jairvol28.php)。
本次实际读取arXiv完整31页，重点§2.3/Algorithm1及§2.3.1–2：加权优先序先找解，
完整解后继续搜索，安全剪枝使用未加权admissible bound，改善已关闭节点必须重开。
论文在生成goal时更新incumbent；这不自动给“首个生成goal”传统pop-goal WA*近似界。
AAAI镜像fetch502，链接与出版身份已从primary目录核实，内容实际取作者版本。

也核实Likhachev/Gordon/Thrun的
[ARA* NIPS2003作者PDF](https://www.cs.cmu.edu/~ggordon/nips03/maxim-ggordon-thrun.ara.pdf)及
[CMU完整证明TR](https://www.cs.cmu.edu/~ggordon/mlikhach-ggordon-thrun.ara-tr.pdf)，其多轮权重下降是另一策略；
本轮**不实现ARA*/动态权重/重启/beam组合**，避免多因素更改。

## 唯一策略、动作族和数学目标

固定**w=2**，heap优先key `(g+2h, h, insertion_counter)`，先A再B生成，完全确定性。
matcher、输入、pair选取和排序、parent<=96、角色定义、逐原deadline COPY、原有序args、相同初始incumbent均沿用R164。
状态仍 `(i,j, exact_role_ages)`，仅完全相同状态保留较小g。不新增早COPY、角色排序、别名、GET重读、重算或结合律。

完整输入有N条原指令，局部开始前已有p条原指令与P条真实物理行。
状态完成i+j条局部原指令、累计局部C条COPY。定义

```
g(s) = P + i+j + C
h(s) = N-p-i-j          # 尚未发射的原指令，含parent与固定suffix
f(s) = g+h             # 安全完整输出行数下界
f2(s) = g+2h           # 只用作访问优先序
Goal cost = 完整原block物理行数 = N + 全block COPY
```

每个side原动作代价`1+该原发射前真实deadline COPY数`；parent同样计。
parent可执行后从真实出口年龄逐原恢复固定suffix，作为完整terminal completion，精确计suffix原行+COPY。
所有原节点仍完整一次，所以在**完整goal之间**最小N+C等价最小COPY；局部COPY最小不一定全block最小。
h只计未发原节点，不计不可证明的未来COPY，因此admissible且原动作中consistent。

已有全block incumbent给U=N+COPY_incumbent。只用**f>=U**剪枝，不用f2剪枝。
完整goal生成即全物理恢复并sink保存，验证成本留实验producer单列；U只在完整、成本一致输出后降低。
不输出未完成局部program作为解。重复state若发现g降低，重新入heap/reopen；路径采用immutable predecessor记录，
避免后来更新best-g导致恢复到不同历史。heap stale版本直接略过并计stats。

即使传统WA*可证明`N+C <= w(N+C*)`，也只推出`C <= w*C*+(w-1)N`，**不是COPY乘法w近似界**。
这里还包含生成goal更新、预算及16出口限制，首个提案不报告w-bound。
无额外portable证书，不给partial输出附optimal标签。
初始incumbent的COPY时机未假设属于本deadline族：安全剪枝可以证明“该候选族没有更好的提案”，
不能在U来自族外时声称U等于族内最优，更不能称原DAG最优。

## 总预算和完成状态

总absolute deadline仍从wrapper首次动作开始，**500ms**覆盖原baseline成本读取、parse/matcher、scan/rank、heap、parent/suffix恢复、全emit和sink。
processed预算仍**累计20,000**，每次有效非stale/nonpruned expansion计1，re-expansion也计1；不能每pair重置。
记录旧DP processed与新heap expansion计数口径差别；同20k只是相同上限，不等同每stateCPU费用。
每pair最多**16实际完整候选出口**，达到限制则`partial_outlet_limit`，不冒称完备。
超时/状态限额为`partial_budget`，全部先前complete proposal保留，旧incumbent始终fallback。
OPEN真正耗尽且全部转移已生成才是`exhausted_improvement_search`，其作用域只有该固定pair族。
timeout在单次expansion或suffix恢复中途发生也unknown，不把未生成后继遗漏当closed证明。

必须记录新增轻量instrumentation：有效expansions/reopens/stale/pruned、最大progress、首次完整proposal所需states/时间、
每progress expanded count、实际OPEN count/max-live；终态unfinished state列表含真实(i,j,roles,ages,g,版本)可在producer事后序列化，
完整serialization成本另列。timeout中途动作必须标`unfinished_expansion`，不提供未经完整coverage的OPEN lowerbound。
R164缺失frontier不复跑为假baseline；同一个冻结实际输出作为质量基线。

## 完整小反例与独立gold，先功能后84

完整12原节点仍用`tree-subtree-12-input.json`，两个含真实二元分支的5节点侧、parent10、SET11；不删节点。
冻结已核验见证：串行0..11为1COPY，`[0,1,2,3,5,6,4,7,8,9,10,11]`为0COPY/max distance4。
这是已知合法候选及非负成本的0COPY最优，不宣称拟议AWA*在某state/time内已经获得它。
预算1不能发射完整12，unknown/fallback必须保留；不能以“anytime”掩盖首解存在等待期。
小状态限额对照将实际记录首次完整候选的处理数，与旧层DP真正0complete限额比较，不提前填假速度数。

阶段1：沿用R163的**固定40输入/8960 raw merges**及原gold证据，不新增更容易测试替代。
独立gold原parser/set-emitter不导入新搜索/state/缓存，保持全6602legal/2358 restricted记录；允许只读取冻结gold不重算oracle。
目标验收`retained_best == min(保存baseline,独立固定merge最优)`：完整结束必须一致；预算/出口partial时必须保留真实unknown，
任何候选不得低于独立gold，所有actual完整输出保存四验证。max-outcomes16也可能产生partial，不能靠增加出口掩盖。
加边界：原COPY/hazard/宽度unsupported failclosed、maxstates1、1e-9时间、goal后注入deadline保留complete、
best-g下降reopen/pathversion恢复、stale heap不作为新processed、外部roles/SET/unused GET/orderedargs完整保持。
仅测试heap算法独立gold作用域，不称任意DAG最优。

阶段1root核验通过后才申请同一固定84；质量基线精确R164全84实际输出，
也单列对原R155/R156以免累加gain误归因。仍65合法+19proof全部保留，每pair来自同初始baseline，不连续组合。
同500ms/20k/16/96，保存所有completed（包括更差/partial）、所有unknown和完整物理输出/originalorder/SHA。
报告COPY/输出与COPY/原两口径、完整status、每次真实candidate/verify/I/O时间；不作隔离性能宣称。
全336与默认auto不执行、不promote；失败不能靠更改分母/删难图规避。

## 继续的判断

当前只授权静态方案，未运行拟议搜索。预计有利于先产完整候选，但不承诺COPY收益；
heap/reopen、suffix恢复和sink有额外开销。若只提高complete率而COPY没有下降，单列资源/覆盖结果。
若发生正确性错误立即failclosed，不将gold范围缩水。若40金标或84仍无收益，不追加w参数网格/预算，以真实前沿评估是否停止该方向。
