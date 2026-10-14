# AVX-512F 隔离研究选项

普通 `build/cholesky_runtime.exe` 的已验收 4f73 版本与 memory 历史二进制继续冻结。新选项 `CHOL_BUILD_AVX512_KERNEL` 默认 OFF；只有单独启用此选项的行优先构建接受 `--simd avx512`（及用于同二进制对照的 `--simd avx2`）。`--simd auto` 仍采用现有 AVX2/portable 路径，AUTO 的块尺寸和结构策略没有变化。此选项不能与 `CHOL_COLUMN_WORKSPACE` 组合。

```powershell
cmake --preset local-mingw -B build-stage2-avx512 -DCHOL_BUILD_AVX512_KERNEL=ON -DCHOL_TEST_ARTIFACT_LABEL=build-stage2-avx512
cmake --build build-stage2-avx512 --parallel 2
ctest --test-dir build-stage2-avx512 -j 1 --output-on-failure
build-stage2-avx512/cholesky_runtime.exe --metadata artifacts/stage2-metadata-wire/page/schema2-dag.meta --input input.bin --output output.bin --engine tiled --structure dense --tile-size 96 --threads 16 --simd avx512
```

CPUID 实测本机支持 AVX512F，XCR0 为 0xe7；检测同时要求 XSAVE、OSXSAVE、AVX、AVX2、FMA 与 XCR0 的 1/2/5/6/7 位。启动和检测翻译单元使用基础 ISA；仅新增 kernel 翻译单元使用 `-mavx512f -mfma`。缺任一条件，显式 avx512 在进入 kernel 前报错；auto/portable 不进入 AVX-512 翻译单元。独立注入特征测试覆盖六个缺失 feature 和五个缺失状态位，不需要在宿主禁用 ISA。

新 U 更新内核一次处理四行、十六列，使用八个 ZMM 累加器；每个单元的 k 顺序及操作数顺序保持原 C。普通源码只采用独立乘法、加法，显式 fma 源才使用 fused intrinsic/`std::fma`。P/T 面板和输入扫描仍走已有 AVX2 实现。尾部逐行采用有界八列加载和标量列尾部，三角区域及 stride padding 不被写入。没有全局 `-march`、浮点重结合、隐式 FMA 或按源码名字/哈希选择算法。

原 AVX2 四行八列热循环没有 k 循环内向量 spill，因此本研究的假设是减少循环、广播与指令编码开销。新汇编确实使用超过 16 个向量寄存器，但 AMD 官方 Zen4 架构资料说明其内部采用两次 256 位操作处理 512 位指令；这些事实不能直接推导吞吐收益。Intel ISA/Intrinsics 和 AMD 原始资料链接与检测、汇编的 SHA 保存在 `artifacts/stage2-avx512/initial-plan.json`。

已通过 16 个独立 IEEE754 位 golden、1400 个保护页/尾块/三角边界组合；240 次 actual C 完整文件对照覆盖朴素、官网转录、分块和显式 fma 源，以及 subnormal、大数、近秩一、符号零、稠密输入。每种源都有 AVX2/AVX-512 同几何对照和 auto/portable 回退验证。隔离构建 9/9 CTest 通过（181.45 秒），原流水线 405 个文件比较与 53 个拒绝保持；新 AVX-512 功能证据单独保存在 `artifacts/stage2-avx512/correctness/report.json`。

预声明计划 `artifacts/stage2-avx512/performance/run-plan.json` 固定 N6145/8193/10000、B96/B128、16 线程，五轮交替 AVX2/AVX-512，共 60 次；执行前新增 `run-plan-v2.json`，仅强化每 trial 原 C 源/input/oracle/Metadata/EXE 的完整 SHA 复核，几何、轮次、二进制不变。6145/8193 已用于上一块尺寸研究，本次不能当作新的 heldout 样本。

协调的独占 CPU 窗口中，实际 session 45883 正常 exit 0，60 次完整原 C 输出逐字节一致。整批 222.887 秒包含 58.947 秒独立 SHA 复核及文件对照；单次 SHA 核验中位 956.296ms 单独记录，不加入 runtime 的 compute 或 IO 成本。每个 trial 的 compute/graph/kernel/export/Metadata/输入输出 IO/进程 wall 全部保留在 `performance/performance.json`，没有丢弃长尾或重跑负值。

| N | B | AVX2 compute 中位 / 范围 ms | AVX-512 compute 中位 / 范围 ms | 中位变化 | 五对中更快次数 |
|---:|---:|---:|---:|---:|---:|
| 6145 | 96 | 495.078 / 459.349–550.422 | 449.022 / 417.785–571.477 | −9.30% | 3/5 |
| 6145 | 128 | 421.766 / 408.653–602.471 | 517.737 / 473.935–524.961 | +22.75% | 1/5 |
| 8193 | 96 | 1047.960 / 985.155–1143.340 | 984.150 / 899.270–1050.290 | −6.09% | 4/5 |
| 8193 | 128 | 1030.530 / 1001.380–1058.710 | 988.305 / 962.586–1051.510 | −4.10% | 4/5 |
| 10000 | 96 | 1701.700 / 1633.210–1803.590 | 1699.270 / 1640.960–2461.680 | −0.14% | 3/5 |
| 10000 | 128 | 1603.160 / 1530.730–1750.360 | 1588.340 / 1545.000–1677.660 | −0.92% | 4/5 |

表中的变化是两组中位之比，各轮配对比值另外完整保存。30 对中 11 对负面；最差 N10000 B96 repeat1 为 1633.210→2461.680ms（+50.73%）。N6145 B128 有四对负面，N10000 完整 compute 中位基本没有收益。不同 N/B 的结果不支持普遍提速结论；不拟合阈值、不升级 auto，不由指令减少推断收益，也不推定官方 85 分。AVX-512 保留为显式研究选项。
