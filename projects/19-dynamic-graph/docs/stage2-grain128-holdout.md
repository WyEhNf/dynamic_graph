# 19题：B128独立Shape验证

此次预先固定fresh N6145、N8193及旧N10000复验，16线程比较实际`--tile-size auto`与显式B128，各五轮交替，总30次。实际AUTO每次报告B96；同一冻结Runtime SHA为`d84bda7e70790b4b751aee0a877c0457f50bf9c95b086d35c1738be31061c8f2`。没有修改kernel、默认策略、数据特判或阈值。

依据仍为[LAPACK DPOTRF分块实现](https://www.netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html)和[2026年OpenMP/HPX Cholesky论文](https://arxiv.org/abs/2606.11937)关于任务粒度和调度开销的讨论；本次测量验证本项目推断，不移用原论文机器成绩。原C每位置FP64运算顺序不变。

新参考由冻结的官网算法转录C独立GCC编译执行，采用既有明确本地契约：div为x/y、madd为非融合x*y+z、L初始+0，编译禁fast-math和隐式FMA。实际C生成参考，不使用candidate或Python矩阵计算生成真值。输入仍为原有对称强对角占优dense生成族；“fresh”指预先未测的新Shape及尾块，不表示新数据分布。

| 新Shape | 输入生成秒 | 实际原C参考执行秒 | 完整参考字节 |
|---:|---:|---:|---:|
| 6145 | 18.538 | 96.004 | 302,088,208 |
| 8193 | 31.266 | 327.673 | 537,002,000 |

参考准备总475.718秒；N10000缓存source/input/oracle SHA复核后沿用，不计新数据。各实际源、C harness、GCC程序、输入及结果SHA保存在`artifacts/stage2-grain128-holdout/reference-preparation-v2.json`和各fresh目录的`reference-provenance-v2.json`。v2在任何candidate执行前修复记录中的路径字段，原C文件和其SHA未变、未重算原C；原记录及计划仍保留审计。配置集合、source-order算法和二进制保持原样。

独占CPU窗口内完成30次，80.590秒，全部完整输出与原C字节一致，包括头部和完整矩阵。成本采用完整compute，含分配、输入验证、图构建、调度、kernel和导出；Metadata、输入/输出IO及进程wall另列。所有单次值、每形状五个配对比例及区间保留，无丢弃负结果。

| Shape及角色 | AUTO B96 compute中位ms | B128 compute中位ms | 中位变化 | B128获胜配对 |
|---|---:|---:|---:|---:|
| 6145 fresh | 465.376 | 431.869 | −7.20% | 5/5 |
| 8193 fresh | 1020.390 | 941.361 | −7.74% | 5/5 |
| 10000旧Shape复验 | 1622.870 | 1502.880 | −7.39% | 4/5 |

两个fresh Shape的五个配对均改善，但完整区间仍重叠：N6145 AUTO 434.021–485.290ms、B128 419.151–451.587ms；N8193 AUTO 973.232–1107.460ms、B128 934.391–1020.070ms。N10000第4轮存在反例：AUTO1569.710ms、B1281581.980ms。该结果支持在已测dense族、16线程及这三档Shape下继续考虑B128，尚不足以保证所有Shape/worker/source通用收益或官方计算85分。

**默认仍保持原AUTO策略。** 当前代码已提供显式`--tile-size 128`；没有根据上述结果临时拟合新的N阈值。若要形成通用策略，需要覆盖其完整作用域并保留小Shape或线程档的潜在回退代价。完整证据见`run-plan-v2.json`、`performance.json`和`comparison-summary.json`。session71017正常exit0后CPU性能窗口已经释放。
