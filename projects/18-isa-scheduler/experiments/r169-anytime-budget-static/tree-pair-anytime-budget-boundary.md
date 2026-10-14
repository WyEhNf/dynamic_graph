# R168预算边界静态审计（不覆盖历史；待root审）

R168实际source aggregate `1d3731c7117e1421836899002d8e733862c92f416e07b9664f80513f5a42387a`，
core `4578aadd67b078690da476de858dfaea943f1932c1418f52e5e9911f2f244354`，
report `7876b9b6f6f16660a36e104ed10c9a7a2135392a6a1ac4b91b17bfe6c6da9be8`。
本文只读已冻结来源、实际记录，未修改R168、未重新运行40/边界/旧gold。

## 已实际发生的边界

core的try/except覆盖prepare、search、parent/suffix恢复、完整emit、sink，均检查同absolute deadline。
预算停止之后，`raw_frontier = [...]`仍调用`agenda.frontier()`、读取各pending role-age并用`active()`建roles；
它位于最后check或catch之后，没有被deadline check覆盖。
返回`elapsed_ms`在上述materialization后采样，因而包含该成本。
R167预声明是producer事后导出/JSON序列化单列，当前R168实现尚未完全实现这一诊断边界分离。
**没有保存独立search-stop/materialization两时钟，不能事后填实测耗时。**

40实际均`exhausted_improvement_search`，`actual_open_count=0`：这一批末尾没有unfinished frontier角色构建，
但这不证明在partial输入上没有成本或满足硬wall上限。
未知边界的函数返回中包含实际OPEN/unfinished对象；test producer只保存了5份完整物理输出，
没有把该unknown返回stats导出为历史证据。不能称R168已保存所有partial前沿供独立复核。
核心可检查实际counter的测试通过，不等于独立保存了每次partial状态。

40真实reopens=0、stale=0；synthetic `_Agenda`的reopen/immutable-path/stale测试明确仅为队列契约，
不当作实图reopen覆盖。固定40全部与原8960独立gold匹配的输出正确性/成本结论仍保留，
不从此推断84收益、COPY乘法界或默认资格。

## 建议唯一诊断修订（尚未实施/测试）

1. 仍同固定w2、matcher、原动作/COPY时机、f剪枝、parent/pair策略、500ms/20k/16/96。
   不改搜索算法、数据族、预算或质量分母。
2. 在返回控制权前记录`search_emit_ms`及`stopped_phase`。OPEN count、reopen计数、expanded-depth等已有常数时间字段放stats。
   未完成扩展仍unknown，不能把其未生成后继从闭合证书遗漏。
3. 以返回diagnostics保留已经存在的immutable label、pending索引集合、exact ages、canonical roles缓存和unfinished扩展。
   不在截止之后循环materialize全部state/role列表。初始prefix角色缓存应在受deadline覆盖的prepare内建立。
   函数返回后不再修改这些容器，旧label path不重写，producer导出时不会观察到后续搜索变化。
4. 单独`export_frontier()`只在producer事后调用，真实导出所有当前pending版本及unfinished状态；
   它与JSON写盘分别计时，报告`search_emit_ms`、`frontier_export_ms`、`evidence_serialization_ms`与whole-candidate调用墙时。
   这些诊断成本不能被称受500ms硬wall保证；原预算是搜索/恢复/完整sink截止。
5. 保存边界每次真实完整result的stats/frontier及已有完整输出。root允许后，仅补6项边界证明该诊断范围，
   不重跑40gold、不改历史R168。新独立证据目录注明actual source与修订前后哈希。

当前不启动新CPU任务，84仍未授权。此修订也不为任意partial输出加optimal或infeasible标签。
