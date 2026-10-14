# R173：ca93 保存证据的出口受限回归归因

输入 SHA `ca93bf4ab93ad82421ae4da463775dc2d4c7ceb7bfdaba399a02f1588a2c0b9d`，ragged_tree，64 原节点，W4。原 incumbent23 COPY；旧 R164 DP21；R172 AWA23。此处没有重跑任何策略、baseline 或 oracle，以下全部来自已保存完整 outputs 和原始 JSONL 前沿。

AWA 固定 selector 首先尝试 parent62，3826 expansions，0 完整提案，OPEN0，约61.939ms；仅说明该初始两侧固定序/到期 COPY 候选族没有严格改善，不是一般 DAG 最优。第二次尝试 parent61，3754 expansions，16 完整提案，约86.226ms，在 complete_outlet_limit 停止。wrapper 合计7580 states、约149.064ms，低于20k/500ms，故不能归因为时间/状态预算不足。

16 份完整提案均 parent61：31 COPY两份、30两份、29两份、28两份、27三份、26两份、25两份、24一份；全部合法（根 R172 已独立重放），但都未胜过原23。最先完整提案31 COPY，于3614 expansions产生。没有 first improvement。parent59 排在第7；wrapper 在第二 pair 的16出口限制时整体停止，没有尝试 parent59。旧 DP21 的 parent59 witness 未被串行补回。

原 DP21 的原节点 order 投影到当前 parent62 的两侧，第一侧首次偏离 offset39；投影到 parent61 的两侧，第一侧首次偏离 offset10。因此**这一个已保存的21见证**不属于已尝试两个 pair 的固定 side order 族。不能由此排除另一个21见证，也不能说 parent61 已穷尽。完整投影与全部实际提案 order 保存于 `experiments/r173-anytime-ca93-static/report.json`。

parent61 返回的实际3个 OPEN 为：

|i,j|roles|ages|g,h|g+h|label version|
|---|---|---|---|---|---|
|0,26|52,54|1,2|33,38|71|3592|
|1,8|25,39,41|1,2,3|10,55|65|2681|
|1,29|25,60|3,1|39,34|73|3730|

unfinished 扩展为 i14,j29，roles37,57,60，ages1,2,4，g57,h21（g+h78），label3756，next_side0，reason expansion_in_progress。原完整 incumbent 行数 U=64+23=87，旧21见证85行。以上 g+h<85 只说明安全必要 floor 尚未排除更优解，**不保证 continuation 能形成85行或任何完整解**；没有续搜、没有反造目标、没有修改 saved clocks。3757 immutable labels 和实际 OPEN/unfinished 原证据链接/哈希冻结。

唯一已证实机制是：固定父 pair 排序 + 第二 pair 的16个已完成出口阻止后续 parent59 被尝试，保留原23导致相对旧 DP21 的2 COPY退化。R174完整336计划保持此语义，不改 ranking、16出口、权重、预算，不用旧DP fallback掩盖回归。
