# R180：一般共享 DAG 的有界区域重排——单一下一算法设计

**当前仅设计/静态冻结，不实现、不运行solver batch、不升默认。** R178及原R107/143/各TeX保持原件，11继续暂停。准备根审后先功能gold，再原固定全集/新共享持出，不直接全336实验。

## 真实剩余贡献与选择依据

R179读取原21族/336所有状态和R178保存完整输出，用真实COPY的原identity/op归因，再按同输入SHA接已独立审计R143 necessary bound。没有重算新界/调用任何调度器。原272/47/9/8仍保留，只有272有实际C；C−L是可改善量**上界**，L0可能很松，不能承诺达界。

- near_window_spine C135089/L134208，gap881；其对272等权COPY/输出的潜在改善上界仅0.0708个百分点，不因COPY绝对量大重复探索。
- ladder_diamond C8334/L8330，只剩4；不再挑此族作主要算法收益来源。
- cross_group_shared C9755/L7956，gap1799，9746COPY为GET身份；sparse_shared C4997/L4028，gap969，全为GET；stencil C1356/L0，全族1352COPY为GET但该界可能很松。这些共享身份/消费者时序是新增覆盖的优先诊断。
- dot_product_many C2876/L1677，gap1199，其中2448COPY为ADD累加器，不能把所有共享问题误称GET缓存问题。
- 树 padded3892/ragged4039/balanced2195 的L0不证明可零COPY。新方法同样覆盖树更自由原拓扑交错，但不继续固定两侧pair再单纯加出口。

R178仅25树图可搜索，133合法图因shared/hazard等matcher限制而未尝试，108已零COPY/6无pair、64缺incumbent全部保留。16状态预算、7时间截止、2出口cap是本次25搜索的实际partial原因；不能把有baseline保障说成搜索已最优。

下一变化是**去掉固定树/两侧prefix候选空间，按实际DAG依赖枚举区域内任意ready原节点**。它增加共享算术/共享GET/内存hazard/死值等真实覆盖；不靠增加cap、删难图、放宽原语义。它仍是区域neighborhood，不冒称任意大DAG全局求解。

## 一手文献与适用区别

[Sugita等CC2023作者PDF](https://www.rsg.ci.i.u-tokyo.ac.jp/lab/en/assets/files/cc2023-sugita.pdf)，DOI10.1145/3578360.3580263。本地已读PDF SHA14c6bdb5...；本次网页再次fetch超时，使用已冻结完整原文。其活动值/窗口搬运论证启发真实年龄状态，论文spill与SSA处理不能搬作赛题许可。我们仅保留COPY/重排和必要hazard。

[Gang Chen，Min-Reg，作者v4预印本](https://arxiv.org/abs/2303.06855v4)，2023-11-21版本，本次实际重读。论文用CP-SAT对照寄存器压力启发式，指出共享DAG与树有不同难度；适合借鉴真实ready/最后消费者信息。我们的主目标是COPY，压力只作邻居生成次序，不是COPY下界或优化保证。此前逆向MinReg原336失败/退化已保存，不能重复将它默认。

[Hansen–Zhou，Anytime Heuristic Search](https://arxiv.org/abs/1110.2737)，JAIR28(2007)267–297，DOI10.1613/jair.2096，本次实际重读。采用固定w2访问、unweighted admissible f剪枝、exactstate low-g reopening、完整incumbent保留；没有ARA权重网格/重启。原完成数+COPY目标与COPY排序等价，不能把weighted完整行数保证冒称COPY乘法近似保证。

[LLVM当前GenericScheduler官方实现说明](https://llvm.org/doxygen/classllvm_1_1GenericScheduler.html)，本次实际读到LLVM24.0.0git文档。真实ready依赖、压力变化及区域调度是工程参照；其target latency/硬寄存器/双向边界不等于本距离ISA。此次不依赖LLVM安装，也不声称实现LLVM策略。

## 固定区域与原输入合同

新文件计划 `isa_scheduler/general_region_anytime.py` 和一个显式wrapper，不改现有treecore/default。仅原COPY-free GET/SET/ADD/MULW、官方bits2..5；未知opcode/格式fail closed。保留每原恰一次、有序args、reg和RAW/WAR/WAW，不做GET重读/别名/重算/spill/删节点/重新结合。

以**同一个已独立四验证的完整incumbent**原order为基座。固定region最多32个连续原节点；候选start为16 stride的原rank网格，对每个发生COPY的cursor取所在网格与前一网格两种start，末端clamp，去重。保存本region原COP数排序（降序，start升序），固定最多64region。这个上限是资源保护且必须在报告中列出未覆盖区，不由oracle/新输出挑region。没有纯树/私有值/独占寄存器筛选；shared arithmetic、shared roots、重复有序输入、unused GET、SET、多sink与hazard都可进入区域。

整块原prefix物理行逐行保持；固定suffix仍按原incumbent原order。只重排region内原集合，所有区域proposal来自同initial，不叠加gain。任何新结果保留原完整block/order，不能只报告local COPY。32范围不能移动跨很远prefix的GET/消费者；这是明确覆盖限界，不保证消除1799 gap。

## 精确状态与合法转移

本region完成集合用32bit `done_mask`；prefix原完成集合固定。状态是 `(done_mask, tuple((original_identity, latest_age), ...))`，按原identity排序，包含**所有**未来数据消费者尚未发射的已生身份：prefix外部roles、region内部共享身份、结果被suffix消费的身份。不同真实identity不合并，不做shape年龄对称/等值别名。

每个identity的region消费者mask及suffix消费者count由原data edges重建；same mask决定剩余directusers/live，不把memoryorder边当temp活跃用途。RAW/WAR/WAW仅限制ready：依赖在prefix已满足，或region内mask已完成；合法原incumbent连续region保证内部节点没有尚在suffix的前驱。所有ready原节点都允许生成，保持原有序args；重复x,x只消耗同一真实消费者一次，但输出两个引用仍保留。

从物理latest ages执行**现有到期COPY策略**：若最老live年龄W且本条不最后消费它，COPY该identity的latest副本并增龄；若到期identity本条最后消费，可直接发射。未到期不early COPY。至多W−1旋转即可找到dead/last-consumed槽；旋转W次仍不能发射，记此state/动作受限失败，不称整图无解。一般共享操作数只有remaining消费到0才删除，非最后消费不会被emit自动刷新。结果只有有未来data consumer才保留live；dead GET/死算术/SET同样推进物理槽，SET不产生可引用身份。原COPY格式仍不支持，不能据此给unsat证明。

转移后增龄、删除最后消费、增加真正live结果。相同done和全部真实role ages确定余下合法/成本行为（在latest+deadline COPY候选策略下）；仅严格同state时保留低g，允许reopen。旧副本未被考虑是一种COPY策略限制；不能由state空间穷尽推出所有合法COPY放置最优。

## 数学目标、队列、完整出口

`g=当前真实物理行数`，包括固定原prefix及已生COPY。`h=整块尚未发射原节点数`，包括未完成region和固定suffix；非负且沿一次原发射恰减1，任何后续至少这些行，故g+h为安全完整N+COPY必要floor。用固定 `g+2h` 排访问；只用g+h>=当前**完整合法**incumbent行数剪枝，绝不把启发压力/弱R143界当新的可达证明。R143不额外加入state floor，本轮只用于input-only机会排序。

每次扩展全部ready按固定tuple排序：预计本一步COPY数、发射后live数变化、GET的尚未发射消费者数（非GET取0）、原incumbent rank。这只改变生成次序；不删除ready，不声称min-reg或COPY最优。若为了全局预算只完成部分ready生成，原state/下个ready cursor标unfinished并保留；不能称完整扩展。

region全部原发射后，必须从真实prefix/live replay该区域path及整块固定suffix，逐原算remaining，证明path模拟的region出口物理g/ages与实际一致，最终全原排列/N+COPY一致。仅完整原block emit完并送sink后才记complete；中断partial suffix不作为候选。所有更差/同值complete保存，严格更好才更新best；每region16cap只停止该region，总预算剩余则继续下一region，整体partial保留。

## 不增加预算的资源合同

固定每输入总500ms、累计20k实际expansions（含reopen）、每region16complete；region32/最多64。一般ready outdegree可能32，不可沿用旧pair的2×20k label界。因此另加**更严格**累计20k transition尝试预算（每一次ready动作，成功/失败/剪枝都计）；不把它叫20k expansions，不扩大旧预算。labels至多20000+64 seed，OPEN至多labels；最多1024保存complete。达到任一expanded/transition/time/outlet/resource限制为partial/unknown，不伪证明。报告三个真实量：expansion、attemptedtransition、acceptedlabel，预算分母不同不比较吞吐优越。

每transition角色≤W32、最多W次旋转，朴素代价O(W²)；ready扫描最多32，局部mask查询，模型预处理/完整suffixemit/complete JSONI/O全部计同500ms。20k transitions和20k expansions都累计跨全部region，sameabsolute deadline不暂停诊断/重置。原initial合法输出始终fallback，不恢复缺inc64图或称其解决。

资源沿R177 producer：至少512MiB reserve、当下input标签流式原样导出并逐region释放，diagnostic materialization/JSONIO/验证/end-to-end独立计时。20064labels×(1KiB label+2KiB OPEN)+64header/unfinished预留约62MiB；proposal按完整N包络重新核算，绝不仅按32局部大小。OSError/resource_unknown保留partial/allinput分母，无自动重启。实际布局要在实施前冻结并静态验证字节包络；这些是规划上界，不是已测峰值。

## 完整小反例及下一功能里程碑（需新授权）

`general-region-hand11.json` 手写11原节点/共享GET a两真实消费者，W4。baseline完整14物理行，3COPY；新完整12行，1COPY。order把原GET a从第一移到两个私有子表达式后，原GET仍恰一次，最大t#4，有序ADD/MULW依赖保留。它展示树matcher拒绝的共享根和自由出生顺序，不说明R178已有baseline必差，也不宣称1是全局最优。当前仅手工见证，未跑新solver；根/下一里程碑独立校验。

实施前冻结单一算法/预算/selector/全部输入。先独立raw topological/physical-age小gold（N≤9）涵盖sharedGET/shared arithmetic、重复x,x、有SET→GET hazard/死GET/死结果、多sink、same-state lowg/reopen、引用旧rep的合法gold差异。raw gold枚举可以earlyCOPY，故是更广参照；candidate latest/deadline family可以更差，不能要求伪相等或降低gold覆盖。保存正/阴/unknown全部，closed阴性才证明相应声明模型，不由受限候选失败改unsat。

固定手写11两完整witness先四验证，再新算法一次；检查是否真的产生完整≤1，不预承诺。单输入1state/tinytime、budget在successor中途、完整goal后中断、firstregioncap后second改善、unexpected opcode/原COPY拒绝、suffix/outside-memoryhazard、外部sharedroles未最后消费等边界保存actual rawlabel/unfinished。

gold审后再从R179机会排名选择原shared/stencil/sparse/dot每族预声明完整输入，以及新共享/内存hazard持出，始终与同R178真实incumbent比较、保留所有unknown/partial/noinc，不能把新的更容易族当Level。所有实际完成block先原身份/符号/三整数四验证。若没有实质收益，原样报告，不加budget/cap，不升默认，也不急着重复整个336。
