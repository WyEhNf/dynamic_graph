# R47：dependency-ready affinity 初态的质量负结果

此批以冻结 R45 为基线，不采用 R46 的阈值改动。只将12个 affinity 初态的构造改成在接口偏序 ready 集合上直接选择邻居，保留原阈值、profile、局部移动和16M收费上限；没有增加 seed 数或预算。默认仍为 R44。

该改动的动机是避免无约束社区次序被后续 Kahn 规范化打散。但实际适用35个原失败图的诊断恢复数从 **2下降到0**，丢失 R45 的两个同拓扑参数记录；新6个失败图仍5个适用、0恢复。原61中31次、新6中4次预算耗尽，未解记录保留。由此可见，先建立无约束共享输出次序、再按依赖规范化，有时保留了更好的全局优先级；贪心 ready 限制并非自动改善质量。

没有新恢复，因此不开展完整202+48功能批或性能配对，不晋升。R45 两条有效恢复的历史源/原计划保持，R47没有替代它们。

实际495个独立Python full-ancestor/live-set bigint profile、permutation、capacity控制通过。另对100k工作上限搜索得到的 **138条实际次序**由独立Python重新验证：完整原始ID恰好一次、每条原始依赖前置、BEGIN W+O、最后直接消费者END释放、sink保留、两类核数和串行零Event deadline。全部通过。这是语义控制，不能抵消真实困难图的质量退化，也不是普遍有解保证。本批没有新运行UBSan。

实际终态：两个顺序GCC O2编译session18846 exit0；`run_diagnostic_batch47.py`完整批exit0，profile、bigint、hard、heldout四个子进程均exit0。低可用RAM期间避免双编译。所有时间只记录共享CPU功能执行成本，不推导性能收益。

源 `research/batch47/solution.cpp` 实际字节SHA：

`236700f9343a802bc136df6e037d8f96145cdb33fc7b7344872451d65550a8ad`

`research/batch47/functional-checkpoint.json`记录实际编译输入、EXE哈希、原始诊断计划与子进程状态。复现：`scripts/prepare_batch47.py`、`scripts/run_diagnostic_batch47.py`、`scripts/review_projection_search_batch47.py`。该批未修改默认源、任何测试期望值或困难输入。

下一方向是根据**原始直接消费者集合**寻找2–4个目标的小组，评价成组移动能否跨过单节点插入的局部最小。分组只提供移动候选，不能合并真实输出、删依赖或获得提前释放。优先保留 R45 有效初态，失败-only 宏搜索和预算增加不作为本次负结果的补偿。
