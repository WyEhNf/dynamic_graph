# 第19题开发验收：完整 Metadata 编码与读取器优化

2026-10-14在四题代码、探索报告和验证材料的 Git 基线 `09868ad` 上继续开发第19题。题面及算法截图已经核对并归档，见[题面要求与来源边界](task19-requirements-2026-10-14.md)。本轮主测试明确使用三种真实 Cholesky C 源码；一般 VM 测试保留为兼容性和反硬编码控制。

## 已安装的成果

新增显式 `--symbolic-format packed`，将表达式操作名、记录字段ID、共享字段存在位图及安全枚举编码合并，完整保留符号图、PROGRAM 和任务依赖。最小策略从八种完整编码选择实际最短文件；普通默认 schema 2/dag 保持，46份上版默认文件重生成结果全部逐字节相同。格式定义、逃逸规则和解码 API 见 [Metadata协议](metadata.md)。

运行时跳过无参数单字符指令的 stream 构造，用线性 ASCII 语法识别替换 schema 3 数字参数的正则检查，数值转换仍使用原 stream。没有改动矩阵数学、浮点运算顺序或默认块策略。两套构建的原始归档对象核对表明，仅 `runtime.cpp.obj` 改变；local其余8个、memory其余6个原始对象与上版一致。

普通 CLI/core 已安装至 `build/cholesky_runtime.exe` / `build/libcholesky_core.a`，SHA256分别为 `eb76a7b27e4570ee7abeb91fade28a85f236b5314422fe8d9636a68d3aaf4a96` / `3a81466f5e1a05449ee512e892778daf6bee07c725df74bf792d92b926765772`。memory CLI/core在 `build-memory`，SHA256分别为 `8189d494c80c9b7e1d3a5beeffeca94670391c55909ad0ee481c0340b8f829f2` / `4347268910f54bbb6b7a28e99e1a43dd21ed020fa7c6ca87501a79044fbdec57`。旧产品在 G 盘本轮 `rollback` 保留。

## 字节数与实测时间

以下以相同 LF 换行、完整图和原字节码比较，旧最小为 schema 3/table，新最小均为 schema 3/packed。早期报告的 CRLF 数字属于历史批次，不能混用。

| Cholesky C 源码 | 旧最小 / B | 新最小 / B | 本轮减少 | 旧默认schema 2/dag / B |
|---|---:|---:|---:|---:|
| 自设左看式 | 1587 | 1391 | 12.35% | 2119 |
| 官方图右看式转录 | 1777 | 1512 | 14.91% | 2499 |
| 自设分块 | 2377 | 2040 | 14.18% | 3491 |

读取器在同一台 Windows/x86 AMD 主机上，使用上版 S33 与本轮静态库分别编译同一个真实 `read_metadata` 驱动。每类7组 AB/BA 新进程配对，每进程先做一次不计时读取，再做1024次完整打开/读取/解析/关闭/析构；84个进程观测全部保留，没有删除慢样本。使用相同 schema 3/table 文件，配对中位耗时减少分别为左看10.8847%、右看13.0789%、分块12.1291%，各7/7对改善。解析字段、指令和double参数位的摘要一致，随后完整原C比较作数值验收。schema 2/dag对照配对变化分别 +1.2782%、+0.8102%、−1.0722%；后者为轻微负结果。

这些数字属于**重复读取器**，包含文件操作，不代表冷启动、单次 Metadata 读取、Cholesky 分解时间或官方85分项整体改善。题面没有完整定义 Metadata 解析的计时边界，指标分别保留。排名评分不能根据本地改善百分比推算。

进一步对普通稠密 Cholesky 做物理块128与现有AUTO的同EXE、16实际worker、5组AB/BA配对，每次写完整输出，每个尺寸首对逐字节核验原始C。N4099/N6145/N8193/N10000的配对中位compute变化为 −9.92%/−1.95%/+0.40%/+5.71%（正号表示减少）。预设采用门槛要求所有N≥6144改善至少3%、至少4/5对改善且单对回退不超过10%；**未通过，默认策略保持**。首批遗漏 `--scheduler parallel` 而只用了1 worker，已中断并标为无效配置，保留记录，不纳入并行结论。没有把10000单点收益扩展成普遍收益。

## 正确性验收

- local完整18/18 CTest、memory完整13/13 CTest全部通过。后续只增加压缩候选静态检查及Clang路径配置，分别补跑两套 `packed_symbolic_contract` 通过；数学源码和已测二进制未再改变。
- 单列 `cholesky_metadata_pipeline`：三种真实Cholesky × 八种完整编码 × VM/单线程tiled/四线程tiled × dense/含负零对角数据；动态宽度3/7/31/65/129，分块源block1/7/32/100。每套288次完整文件比较，两套共**576次 Cholesky 主测试流**，包含非整除尾块与native边界。参考只由独立编译原始C生成。
- 既有 full/helper/while/integer-selector 流水线亦全部通过，包含一般VM、拒绝与未定义整数边界；这些不冒充Cholesky主测试。
- 独立最小选择测试：6种实源、每源8候选、单次AST/LLVM IR编译次数核对、24次原C VM/tiled比较、5项冲突参数拒绝通过；其中3源为Cholesky，3源为一般兼容控制。
- 两套CLI分别处理普通dense N10000与真正band N10000w7，**4份800,000,008字节结果**全部与已有独立C参考逐字节一致；不重复执行约8分钟的原C大矩阵生成。块实验首对另有8次大文件全字节核对，其余轮仅校验长度，报告明确区别。
- 新数字语法对照独立std::regex穷举/随机共96,441案例与两个十万字符边界通过，原33 opcode、浮点参数bit golden与格式错误合同也通过。
- packed黄金样例、500批字段缺失/null/bool/整数/未知字段往返、非法结构拒绝通过；三种Cholesky的24个完整压缩容器往返及八候选压缩后最短选择通过。压缩仍显式可选，普通CLI没有启用zlib容器。
- 46份上一版已接受默认Metadata重生成字节一致，0跳过。最终215份源码冻结，产品、构建flags与raw对象SHA记录一致。

## 使用与复现

```powershell
.venv\Scripts\python.exe tools\analyze_source.py fixtures\official_naive_transcribed.c --function cholesky --clang 'C:\Program Files\LLVM\bin\clang.exe' --smallest-metadata --output small.meta
build\cholesky_runtime.exe --metadata small.meta --input input.bin --output result.bin --scheduler parallel --threads 16
cmake --preset local-mingw -B G:/Hackathon-stage2-artifacts/project19/rebuild -DCHOL_TEST_ARTIFACT_ROOT=G:/Hackathon-stage2-artifacts/project19/rebuild-evidence -DCHOL_TEST_ARTIFACT_LABEL=fresh
cmake --build G:/Hackathon-stage2-artifacts/project19/rebuild -j 8
ctest --test-dir G:/Hackathon-stage2-artifacts/project19/rebuild --output-on-failure
```

测试证据目录必须使用新名称，工具拒绝覆盖历史结果。普通F盘构建目录仅安装已经在G盘测试的CLI/core，其旧测试产物不作为本轮验收依据。F盘剩余空间较少，新构建/测试产物使用G盘。Git工作目录为F盘，实际Git存储为 `G:/Hackathon-git/hackathon.git`，完整迁移需同时保存两处。

本轮原始证据目录为 `G:/Hackathon-stage2-artifacts/project19/20261014-development/`；紧凑证据包与机器记录保存至 `reports/project19-development-evidence-2026-10-14.zip` 和 `reports/project19-development-validation-2026-10-14.json`，包含源码/协议/元数据/测试报告/构建出处，不含数GB矩阵与旧二进制。本轮使用用户提供的官方页面截图，不声称已取得官方测试包、完整官方分块源码或鲲鹏硬件成绩。

此前19页探索PDF及其证据包继续保留为S33历史快照，没有将它们的旧数字改写成本轮S34结果。下一步最重要的是拿到正式C/helper契约，在鲲鹏ARM64上完成构建、保持运算顺序的向量/布局优化和同环境性能验收。
