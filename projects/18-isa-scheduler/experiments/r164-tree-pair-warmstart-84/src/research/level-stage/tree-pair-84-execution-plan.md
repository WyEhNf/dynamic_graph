# R164 固定84 warm-start批次预声明

实际唯一新wrapper为`isa_scheduler/tree_pair_refine.py`。root已独立复核R163全8960固定merge、6602合法/2358固定次序失败、469完整输出，40固定族成本匹配。先冻结全部实际源码、输入与保存对照来源，再开始候选。

旧48直接使用R155已保存实际incumbents，新36直接使用R156；各原12/7身份模型证书、原unknown输入保留，0COPY无需尝试。不存在合法incumbent的输入没有warm-start候选，不据此把它们改为证明或成功。所有输入均在最终84分母。source旧算法不重跑。

每图总500ms/累计20k processed states、每pair16出口、parent≤96。全parse/forest检查、完整输入/输出COPY归因、subtree闭合判定、排序、DP、恢复、全原emit、输出sink文件写入均占同一deadline。子调用仅获得剩余毫秒与剩余状态；unknown即停止该图，已完整提案仍保留。prepare或scan超时仍保留原incumbent。BudgetExceeded新增processed_states仅用于准确累计，不改变转移/候选序。

排名固定为child-root COPY数降序、当前局部interval COPY数降序、subtree size升序、parent原index升序。它是启发式，不是必要界，没出现收益时不据此改变排名重跑。每pair都读取同份初始incumbent，winner按完整COPY数取最小；不应用此前winner作为后续输入、不组合局部gain。

sink逐complete输出保存每个actual出口，含更差和最终被预算截断的已完成项；不保存不完整物理程序充数。候选阶段后所有保存出口与完整before/best独立原身份/符号/三整数检查，失败直接终止。核算COPY/输出与COPY/原两均值、各分母与失败分类、总states/partial/实际墙时，不能以“仍有旧合法输出”把partial search叫完整搜索。候选500ms不含产生旧incumbent或独立验证；不是全接口墙时保证。

本批为功能验收、可与普通项目工作并行，不作隔离速度因果结论。default、完整336/72质量冻结、旧TeX/PDF不修改。仅此一次84batch，不增加预算或更换容易输入；结果无论正负保留。
