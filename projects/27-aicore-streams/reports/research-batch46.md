# R46：workspace gap 识别的隔离负结果

默认仍为 R44。R45 完整候选的 143/202 与新 48 图 42/48 功能结果已保存，但尚未晋升。R46 仅改变 R45 的接口阈值，不改变祖先闭包、原始存储语义、16M 工作上限、初态或局部移动。

R45 的“非零 workspace 中位值 ×4”会在低 workspace 节点大量为零时落入高 workspace 群，导致新持出中的一个 68 节点图没有接口。R46 在排序后的正 workspace 中寻找整数比值最大的相邻 gap，只有比值至少4才选更大的一端作阈值；无此 gap 时使用最小正 workspace。比值用正整数除法，避免 full-int64 乘法溢出。fanin≥2、strict parent-workspace 最大值、2–512 接口、n≤4096限制保留。名称、seed、生成器阶段、witness 都不参与识别。

这项调整仅扩大识别：原 R44 的61个失败图适用数 **35→44**，新48图中6个失败图适用数 **5→6**。实际独立模拟诊断仍是**原2个恢复、新0恢复**；没有新增可行计划。故不将此候选并入默认，也不宣称覆盖增加就是质量提升。未求解图继续保留，未作不可行证明，亦未开启成本配对。

原2条恢复属于同一个拓扑的两个 root 输出参数，serial T/peak 与 R45 相同。局部 gap 可能被单个极大 workspace outlier 主导，最终只有1个接口而被范围门槛拒绝；没有明显分层的图可能选出太多接口。它是启发式识别，不是对一般 DAG 的完整分解。

**576 个独立 Python 完整祖先/live-set bigint控制**由 GCC 实际通过。新增显式控制包括全零 W、只有一个正 W、单个 MAX outlier、极小 W、非均匀多层及超过512个接口；空投影是明确的受限识别结果。同时保留多根、多 sink、O=0、共享父节点、retention链与超int64 profile。此批没有运行新的 UBSan，不复用 R45 的 UBSan 结果冒称 R46 新执行。

`research/batch46/solution.cpp` 实际字节 SHA：

`56c6d6a07e7f07f86e51a4c54343ccb5ac4dadc0f577a1c93ab1f54a8b25bd9b`

修改与复现入口：`scripts/prepare_batch46.py`、`scripts/make_projection_gold_batch46.py`、`reports/projection-profile-gcc-batch46.txt`、`reports/projection-unresolved-diagnostic-batch46.json`、`reports/projection-heldout-unresolved-diagnostic-batch46.json`。仍使用剥除 witness/generation 的 R45 输入。C++ 搜索及完整验证依赖仍仅标准库和本地题面接口。

诊断与金标运行均为共享 CPU 功能成本；不是固定背景或相同 Release flags 的性能实验。session9608/36465均实际exit0、金标一次exit0后已停止新 CPU 编译和诊断，配合项目19的隔离性能窗口。后续研究先静态分析实际 profile 的局部最小与接口偏序，不以普遍增加预算替代恢复证据。
