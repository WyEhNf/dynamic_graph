# R177：修订版 full336 producer 与预执行冻结

`scripts/research_tree_pair_anytime_full336.py` 分两阶段。当前仅授权 `--prepare`：复制并冻结原 R107336输入/输出/order/report和独立审计出处，写静态 inventory、当前源码、参数/资源计划；不验证/求解/重跑任何baseline。根审查后才运行 `--run` 一次，结果另存R178。已冻R174/R175/R176不改。

生产使用 wrapper582493...（每pair cap后继续、整体partial保留）及 coredac3...。固定w2、每输入500ms/累计20k、每pair16、parent96，同initial全部pairs/noDPfallback/no组合gain，sourcehash在prepare和run开始分别核验。保留原272/47/9/8状态、192929初始COPY、全部21族/336输入。完整原report被复制，47证书和原17失败信息不省略。共享/寄存器hazard unsupported、原零COPY、noeligible、缺incumbent原样进入逐输入报告，不改分母。

## 全输出与验证

正式run在任何候选搜索前，对272个已有保存baseline各独立四验证一次并保存预检查列表；这不是重新执行baseline算法。当前检查使用原JSON identity/order/orderedargs/COPY窗口与registerhazards、独立符号、8signed/16unsigned/32signed三个明确本地配置整数重放。所有新实际complete提案与best同样检查，不读内部调度状态；所有更差/相同/部分中断前complete均存文件。完整best_outputs以JSONL包含每个合法输入，unsupported仍输出原baseline；无输出64例保留原status。

对同272成功集报告before/after总COPY、COPY/输出与COPY/原节点等权均值；全336报告状态/缺输出、所有族、候选unsupported/partial/resource_unknown与实际完成数，质量均值为null因64无完整输出。不得把已保存原证明改名成新增质量改善，或缺失COPY填零，也不声明官方Level。

## 截止与导出

complete sink的实际JSON编码/文件写入在core原截止内，独立记录其耗时但仍包含在search-stop wall中。wrapper所有搜索返回之后才导出当下input每pair稳定labels/OPEN/unfinished；materialization与JSON/I/O分开计时。逐pair导出释放、下输入前清空references；compactstats仅存路径/hash/字节，不主report内嵌巨大前沿。每个完整输出的originalorder都保留。冻结输入/baselinebanks常驻约来源JSON解析量，searchsnapshot只当前input，不跨输入堆积。

500ms是search/emit检查截止，不是整体wall保证。precheck、export、JSONIO、四验证、整个batch耗时各列；不做隔离性能因果宣称。当前还没有实际执行任何R178候选。

## 空间/内存保护

固定reserve至少512MiB。prepare/run起步要求可用空间至少1GiB工程规划量+512MiB reserve；1GiB是预留规划，不是最坏存储上界，不从ca93单小例推导保证。源bundle、R174巨大理论proposal行数上界保留，不能声称盘可容最坏情况。run另读实际freeRAM，至少768MiB才开始，不关闭用户应用。

run根据原输入计出当前input保守标签/JSON字节及single完整proposal包络。累计20k expansions每次至多2后继，labels≤40000+eligible；OPEN≤labels；每pair header/unfinished≤1。N≤16384、W≤32、parent≤96时label包络1KiB、OPEN/unfinished2KiB；实际编码每条检查对应包络，违反则fail closed。完整proposal行数≤baseline_rows+WN；128B/行+16N+64KiB envelope保守计single文件。prepare验证“一个input全部diagnostic+两个最大proposal+64MiB checkpoint余量”小于512MiB。后续若碰到实际不满足包络，不声称证据完整。

每输入前检查reserve+64MiB，不够则不再搜索，但继续保留全部336 record和预检过的baseline；候选标resource_unknown_not_executed。sink先编码实际complete；若可用空间低于reserve+其字节，仍利用预留空间保存这份已真实完成提案，然后抛core已有 `_Stop` 类型，理由 producer_resource_reserve_after_saved_complete。core本体未改，使用已有中断回传路径，保留completed/immutablelabels/OPEN/unfinished；wrapper按原partialbudget停搜索，producer另外标resource_unknown，绝不称infeasible。这个动作仅资源保护，不改变搜索顺序/成本/预算。保存的所有actual出口四验证，余下input原baseline保留。

该input搜索结束后的原diagnostic导出亦利用上述reserve，因此资源停不丢掉当下实际前沿；后续input不再搜索。finalbaselineJSONL/compactrecord仍可在64MiB余量内完成。所有文件逐个写入/记hash/bytes，不删旧成果或用户文件。

如果发生真正OSError而非提前reserve触发，保存实际run-failure/partial文件，candidate_outcome resource_unknown，退出失败且不自动重试；无法写出的证据不能伪称已保存/通过。若其他应用同时填满磁盘导致连失败文件也无法写入，原部分文件保留且进程exit非零，不宣称全336完成。正确性异常亦fail closed，原证据保留；这是实际失败记录而非丢困难图。

根审producer及R177预冻结后再授权一次R178。暂不执行R178/336、84、baseline、oracle或默认promotion。
