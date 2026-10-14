# R181：R180 的 transition 计数与未完成扩展补充

本文件补充R180单一设计，保留已冻结R180文件和全部历史原件。当前仍仅静态，没有实现/求解/验证批。

R180 ready排序含预计本一步COPY数。它必须通过真实年龄转移计算，**不得作为未计预算的额外lookahead**：每个ready动作只模拟一次，在模拟前扣累计 transition-attempt 配额，成功/窗口失败/安全剪枝均计。得到的转移结果临时保存并供排序/offer/goal使用，不再次模拟或再次扣费。不从低成本动作之外删除ready，也不将压力排序当数学floor。

为此每扩展分两个阶段：原ready列表按原rank确定；先逐ready计费/模拟收集transition，然后按R180固定tuple排序并publish。若计时/transition预算在收集中断，原parent保持 `unfinished_expansion`，记录阶段 `prepare_neighbors`、下一原ready cursor、已经attempted数量。尚未publish的临时边没有immutable label，不能伪造为OPEN/已扩展路径；它们不是完整原block提案，允许丢弃临时缓冲。已经其他扩展实际publish的labels/OPEN原样保留。region目标只是局部done，只有完整suffix恢复、全部原节点发射并送sink才算complete。

如果预算在publish/完整suffix恢复中断，记录阶段和下一个ready cursor/实际parentlabel版本；parent不当作完全扩展。所有此前实际完整提案留存；局部成功但不完整的suffix不记complete。没有任一partial预算/出口/resource停止且所有ready发布完才可将该parent标fully_expanded。整体candidate受限策略失败/closed不可冒称更广COPY-onlyISA的global optimal/unsat。

计数恒等式：acceptedlabels≤attempted transitions+每region seed，attempts累计≤20000，region≤64；reopen label同样来自attempt，所以≤20064仍成立。expanded计数在开始该parent真实ready扩展时递增，最多20000，partial准备也计一次；并非将20k attempts冒充20k expansions。临时转移缓冲至多32个，path仍immutable linked引用；不把缓冲跨region/input保留。

当前字节/内存包络按原336最大N≤16384、W≤32；这是本研究资源范围，官方未给最大N。实施API应对更大N显式返回 size_unsupported 并保留已有完整incumbent，不能称官方不支持/原图无解。小block长度不足32时整块region允许，dead SET/GET仍推进年龄。字节包络若实际违背必须fail closed，不能边运行边提高reserve估算或丢记录。

原fixture `general-region-hand11.json` 的两个完整物理列表仅手写设计见证；当前没有将它们记作已测验证成功。根代理可独立raw重放，下一授权功能批再做原身份/符号/三本地整数和gold。
