# R171预声明：唯一固定84 warm-start AWA*批

输入直接读取R164完整84 `inputs.jsonl`，不改原JSON/seed/family/宽度或分母。
初始incumbent严格原R155/R156保存输出（与R164-baseline物理行/originalorder核一致）；不重跑任何旧调度器、gold或oracle。
R164最终best只作同原初始baseline的旧DP实际对照，不能替代新搜索初始输入。

唯一固定w2 core为R170诊断修订版本。独立wrapper完整复用R164的parse/forest/数据闭包、COPY归因、contiguous parent筛选与ranking文字。
总literal absolute deadline 500ms；累计20k有效expansion/re-expansion、每pair16完整出口、parent<=96。
两种processed计数口径差别（旧分层DP vs新有效heap expansion）明示，不将同20k当相同CPU费用。
同初始incumbent逐pair提案，不连续叠加；预算/outlet cap停止保留所有已完成物理候选及原fallback。
每个完整candidate文件sink仍在预算内。总500ms包括parse/matcher/scan/selection/core/search/parent/suffix emit/完整sink。

为了不让诊断导出改变literal deadline，wrapper只保留当前输入的稳定reference，最多当前输入累计20k expansion产生的labels。
整个input search返回后producer逐pair streaming JSONL导出OPEN、immutable labels/predecessors及unfinished，计
`diagnostic_export_seconds`和`diagnostic_json_io_seconds`，立即释放该pair引用；跨输入不保留这些对象。
不暂停或延长deadline，不将诊断开销塞进500ms，也不在主report内嵌巨大frontier。
每个文件与rawinput/baseline/parent/参数联接SHA。prefix/ages/roles/g/h/labelversion可由root原JSON独立复核。

全84的原合法65/19限定模型证明保留；原初始COPY11491、旧DP实际11487。
分别报告baseline→AWA、旧DP→AWA的raw COPY、两种成功均值、全部status/outcome及全部completed/partial；
若新质量不及旧DP则如实保留，不能以新的fallback覆盖旧结果再自称不退化。
所有actual complete候选包括更差/未胜全部保存四验证；结果选min(originalbaseline,actualAWAproposals)。
源、输入、原baseline、R164DP结果与资源参数在实验前冻结。只执行一次，不用反复跑预算挑幸运结果。
实验墙时受普通功能并发影响，无隔离性能宣称。原full336/72/defaultauto/旧Tex不改，不称官方Level达标。
