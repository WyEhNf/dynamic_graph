# R158 静态方案：固定两侧合法次序的一般子树交错

## 本轮依据与仍缺少的证据

R155/R156 保存的 completed 双链候选已经等于或优于其 incumbent；不能从这些记录声称一般子树交错已有真实收益。较大的 padded/ragged 输入仍有预算 unknown，合法保存输出继续保留。

静态读取 R155 原始输入与保存 order，筛选两个 child 至少一个含真实二元分支、整个 parent subtree 在保存 order 连续且两侧交错的情况，结果为空。原保存算法目前只在底部 unary chains 交错，上层二元归约大体串行。因此缓存工程不是这项扩展的收益证据，也不能把已有底部交错改名为一般交错。

可复现真实观察点为原 padded64/W4，输入 SHA `23db7ee39361ed481d300c7e7e56d04a7d267c64601e4abd28cc16ebf824a41b`，R155 incumbent 21 COPY。原节点60的 children56/57分别18/14节点，均有二元分支。物理输出中 ADD56在slot17；执行另一侧过程中，identity56在slots21/25/29/33连续COPY4次，然后ADD60在slot36消费它。不能单纯把ADD56后移：它的旧operand14在slot13，原ADD56已引用t#4，后移会先使该原身份过期。需要保留两个内部活值与精确年龄，并允许较早原发射交错，而不是只移动最终ADD。

原证据保持 `experiments/r155-tree-pipeline-old48/23db7ee39361ed48-output.json`，静态解析脚本 `scripts/inspect_tree_pair_traces.py`。目前尚未发现完整原block的新实际更优order，下一轻量诊断必须先建立这一证据，未获准前不运行求解/功能批。

## 完整12节点构造与手算

`tree-subtree-12-input.json` 保存两个固定子树各5条原指令：两个GET、分别一次self unary运算、二元ADD；合并ADD与SET，共12条。两侧都有二元分支，完全保留有序操作数、不同GET/SET寄存器与原身份。

固定A order `[0,1,2,3,4]`；固定B `[5,6,7,8,9]`。串行完整order `[0,1,2,3,4,5,6,7,8,9,10,11]`，identity4在slot4出生，下一侧5条原指令后才消费，因此至少一次deadline COPY（slot8复制identity4）；该具体串行deadline成本1。

交错完整order `[0,1,2,3,5,6,4,7,8,9,10,11]`，手算最大引用距离4：原ADD4在slot6引用identity2/3，距离4/3；最终ADD10在slot10引用identity4/9，距离4/1；其它引用≤3。因此完整0COPY输出可构造；0为非负下界，说明这一完整小block可达全局0。此文件是专门构造，不是删减困难评测图或已运行oracle结果。它不证明真实旧48/新36一定改善。

## 单一扩展的状态与恢复

保留纯树 matcher、原双链方案、原 incumbent、deadline COPY行为、500ms/20k状态/16出口限制。仅增加固定两子树 order 的交错候选；不同时加入年龄排序对称、早COPY或新的候选portfolio。

对于本条二元parent的固定child order A/B，状态 `(prefixA,prefixB,ages)`。已完成原节点集合由两个prefix唯一确定；真实当前live角色由以下静态条件唯一确定：已经发射且其唯一直接consumer尚未发射，包含两child根等待本parent消费。每个真实live身份及全体external按固定role序列保存年龄。重复操作数仍一份身份，但输出保持两有序引用。剩余directusers由固定序列/prefix推导；不能把free-register demand代替真实物理temp生存。

动作只发射A/B下一条原指令，它的子节点必须已发射。deadline `_advance` 只复制将过期且本动作不最后消费的最老live身份；每次COPY及原发射推进槽，最后消费身份删除，输出身份加入。退出后消费parent的两个真实roots并恢复external出口。相同两prefix与完全相同role ages才能合并并保留最小成本，不采用年龄逐项支配、不把同数值当同身份。

固定A/B sequences应先由已保存合法order提取，用于局部诊断；如果有真实收益，再将本节点DFS/双链已有恢复plan各固定成合法sequence，并限制一组预声明次序，避免同时扩张子序选择变量。cache key包含op、有序重复args的role编码、真实sequence、local角色/consumer映射、全部external角色年龄；恢复plan保存relative `(side,offset)`，每实际原ID发射恰一次、原orderedargs/reg不变。所有matching、sequence构造、DP、恢复、实际emit包含总deadline。

复杂度上界 `(nA+1)(nB+1)*P(W,l)`，l是prefix决定的真实live数，包括external。不会宣称这覆盖任意树的全部topologicalorders或任意COPY时机，也不会把局部空frontier/预算耗尽当不可行证明。

## 分阶段验证（先由根审阅后启动）

1. 第一小批仅原保存padded64/W4 parent60与ragged64保存order的二元parent：固定两侧真实sequence，带真实prefix external ages，比较局部串行成本与DP交错；保存所有更差/unknown和完整原block前后order/output。重放全block才能认定真实收益。若无收益，停止该单项，不先跑旧48/新36。
2. 若真实局部改善成立，12节点边界及独立完整局部枚举：至少一侧二元分支，加入external上下文、原参数翻转、unused GET、多root、不支持hazard拒绝、W2/4/8边界。独立raw emitter/枚举不调用候选内部live/cache；保存全部positive/negative/unknown，固定500ms/20k。只称固定局部order family最优。
3. 单一扩展后固定同旧48/新36各一次500ms/20k，直接比较R155/R156保存实际incumbents，不重跑baseline。所有completed候选即使更差保存完整输出；预算unknown保留旧合法输出；12/7原证书不变。全336/default仍不动。

当前只有静态源分析与手算构造，没有新CPU solver handle，没有新测试通过宣称。
