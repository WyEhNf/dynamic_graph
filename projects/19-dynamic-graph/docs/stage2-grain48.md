# 19题：B48粒度研究记录

此批保持同一个已验证wire Runtime（SHA `d84bda7e70790b4b751aee0a877c0457f50bf9c95b086d35c1738be31061c8f2`），只改变物理tile和worker数。旧默认`2b05...`仅冻结溯源，没有混入本批性能对照；源码、Metadata与原C缓存的完整SHA保存在`artifacts/stage2-grain48/run-plan-v2.json`。

研究依据为[LAPACK DPOTRF官方分块实现](https://www.netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html)和[2026年OpenMP/HPX Cholesky论文](https://arxiv.org/abs/2606.11937)。推断为：更小tile可能增加缓存命中和并行任务数，同时增加就绪队列、依赖发布和任务退休成本。论文中的机器与调度器不同，不能移用其数值成绩；本项目仍维持原C每位置FP64算式次序。

读取当前源码确认AUTO：4线程三个Shape均B64；16线程N2048为B64，N4096/N10000为B96。预声明六组B48/AUTO各三轮交替，另保留4096t16 B64、10000t16 B64/B128诊断anchors，共45次。原计划在任何运行前已由v2修正，v1仍保留溯源；没有根据运行结果改变配置集合。冻结缓存存在且source/input/oracle SHA一致，没有重跑大规模原C。

全部45次输出含头部与完整矩阵逐字节等于独立编译原C，108.086秒。`performance.json`为complete，原native及前端SHA未变。记录同时保留compute、graph、kernel、export、验证、Metadata、输入/输出IO和进程wall；compute包含分配、图、调度与导出，IO排除，不能只用kernel代表赛题成本。

| N | worker | 当前AUTO B | AUTO compute中位ms | B48 compute中位ms | B48变化 |
|---:|---:|---:|---:|---:|---:|
| 2048 | 4 | 64 | 44.428 | 49.273 | +10.9% |
| 2048 | 16 | 64 | 32.485 | 32.202 | −0.9% |
| 4096 | 4 | 64 | 272.088 | 315.281 | +15.9% |
| 4096 | 16 | 96 | 163.542 | 226.540 | +38.5% |
| 10000 | 4 | 64 | 3842.390 | 4323.850 | +12.5% |
| 10000 | 16 | 96 | 1630.310 | 2647.120 | +62.4% |

**B48不推广为默认。** N2048/16线程仅小幅中位收益且区间重叠：AUTO 28.692–33.393ms，B48 26.451–33.022ms。其余五组均为负结果，较大N/16线程差距明显。所有单次结果和区间保留，不能挑出单轮获胜样本当作稳定收益。

N10000/16线程B128诊断中位1557.400ms，相对AUTO B96的1630.310ms约−4.5%；B128范围1488.150–1619.770ms，B96范围1594.300–1650.070ms，仍有重叠。此项只作为下一步候选，不修改默认策略。考虑任何粒度策略前，应单独使用预声明fresh N3073/N6145原C输入与输出验证，覆盖尾块，并保留所有对照。该holdout尚未执行，本批结果不等于完成该验证或官方计算85分达标。

证据：`artifacts/stage2-grain48/performance.json`、`comparison-summary.json`、`run-plan-v2.json`及独立冻结的`source/`和`source-v2/`。性能窗口在session 50939正常exit0后已释放，没有后台基准继续运行。
