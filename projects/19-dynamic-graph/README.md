# 19号：动态算子图编译与并行调度

2026-10-14全量复验与业界对照已完成，评估对象为当前S33（CLI `912c9fec...`／core `e7c9dd7f...`）。206源冻结后从G盘重新构建实际local／memory两个preset，CTest为15/15与10/10，另3项Python单测通过；四类源码流水线810次、完整结构集合760次、Metadata变体48次、最小编码策略48次独立C全文件对照均通过，共1666次成功流和118项预期拒绝。另29条当前CLI最大／混合流完整真值验证通过，覆盖N10000、workspace off/session/trim及兼容最大dense。新local构建所有core／main对象及完整PE有效内容与安装版一致。本次没有替换生产代码；以下旧进度为历史冻结记录。

同机OpenBLAS0.3.30对照完成8组、三对AB/BA/AB、48进程，保留全部冷样本与异常点。dense10000/16线程本批中位whole compute为3338.070ms，库pure factor为1497.982ms、包含所述Python适配成本的wrapper为1610.359ms；共享宿主波动明显，仅描述本批趋势。库因子相对C误差约1.2e-16，却有约3509万下三角位差，不满足指定C全位真值；结构化扫描／复用优势和库band数学优势分别评价，不声称整体领先。检索31项一手来源与benchmark，包括2026 Cholesky-Bench及最新Eigen FP32/FP64库比较。

完整[探索报告](reports/project19-exploration-2026-10-14.pdf)、[原始证据与复现材料](reports/project19-exploration-evidence-2026-10-14.zip)、[验证汇总](reports/project19-exploration-validation-summary.json)已提供。全部当前测试／基准原值、源码哈希、JUnit、实验脚本和公开来源保存在`G:/Hackathon-stage2-artifacts/project19/20261014-exploration`；数据包仅保存小型材料，大矩阵保留路径／长度／SHA，不重复打包。报告区分本次执行、历史冻结、外部异机成果与推断，不代表官方隐藏集或得分。

2026-10-14 05:55当前普通CLI为 `912c9fec8ac5...`，同源core为 `e7c9dd7fa08e...`。已安装联合有限值／带宽扫描和owned结构化输入原地分解；四个对角／带宽7主组的完整CLI compute配对中位减少76.46%–82.16%，进程峰值工作集减少约49%–50%，12/12配对为正。N10000带宽7本批compute约242–298→48–52ms、峰值WS约1531→768MiB；这是结构化owned路径，同批稠密/VM负项和首发wall负项保留，不声明一般稠密提速。全局两新编译开关默认OFF，local-mingw明确ON、memory明确OFF；CLI计划仍per-matrix、scheduler默认serial1、native-workspace默认off，借用输入仍不修改。

显著后一次集中验收核对33份完整候选输出（9,165,240,204 B，缓存原C／派生prefix与重复记录／4I解析真值／FMA基线明确分列）、两版各539 API调用、70,016扫描器全浮点标志保持、三种真实配置及失败清理。加入独立扫描回归与结构化所有权回归，206源码fresh构建的9个实际core对象、main/flags与完整PE有效内容相同，仅库日期／PE时间戳校验和不同，因此交付原样已测CLI/core，不重复大矩阵数值。F已重新configure；F旧objects/tests仍不能证明当前产品。继续工作至09:00，详见[阶段指标](docs/stage-metrics-2026-10-13.md)。以下各时间段是历史冻结进度。

2026-10-14 05:34研发进度：合并有限值检查与带宽识别的组件扫描改善42%–49%，但66次完整CLI筛选仅1/4结构化主组达到5%，未安装、未扩大数值验证；扫描分项不能代表总计算收益。下一独立候选正在优化owned结构化矩阵的整输出分配、清零与复制成本，尚无性能或验收结论。当前普通CLI/core仍为下述S22版本，继续推进至09:00；完整正负样本见[阶段指标](docs/stage-metrics-2026-10-13.md)。

2026-10-14 03:24当前普通CLI为`4cceb9db09ef...`，同源core为`9b9d3e8adb15...`。显式`--vm-plan session`的GNU线程VM可一次证明完整PROGRAM的栈／控制流安全，省去热循环中必然成功的重复检查；无法证明仍走原检查。全局`CHOL_PROVED_OPERAND_STACK`默认OFF，local-mingw明确ON，memory preset明确OFF；运行默认仍per-matrix。三组真实长流session compute配对中位减少8.85%/4.25%/3.69%，进程wall负项及冷短流−4..+7us额外成本保留。显著后一次集中验收通过33种opcode、共享session、栈/错误边界、静态proof浮点环境和25份原C完整流；源码、库、CLI由204文件完整构建/安装收据对齐。新回归用例已加入测试图；添加用例后产物/flags全字节不变，无重复数值套。F已重新configure，旧objects/test EXE仍不能证明当前产品。见[阶段指标](docs/stage-metrics-2026-10-13.md)。数组下标证明已完成静态census和runtime短筛，首轮性能回退，未安装。

2026-10-14 02:27历史运行文件为`e47af9a05111...`，同源core为`6f6c6d31686f...`。新增显式`--native-workspace session-trim`：在带状/对角证明成功后释放本流不用的因子容量，默认off和原session保留。早期三对资源筛选中，dense10000→band10000峰值WS/commit降低约20.3%（391MiB），wall负项及顺序影响全部保留；最终显式策略只有一次最大流资源观测，不声明普遍提速。集中原C/API/异常验收后，修复默认构造的源码兼容；完整对象/可执行代码内容相同的证据连接原验收，避免再跑4GB真值。阶段详情见[指标记录](docs/stage-metrics-2026-10-13.md)。VM跨矩阵自动复用仍未改默认：M2全配对回退；直接后继调度也未达收益门槛。

2026-10-14 01:40已安装组合运行文件 `1afefeadf2fa...` 和同源静态库 `0a012a811949...`：保留线程/输入复用、tile首任务初始化和已有小AUTO串行策略，新增16字节VM解码记录及显式 `--native-workspace session` 容量缓存。缓存运行默认off，VM计划默认per-matrix；local-mingw明确编译缓存能力，全局CMake开关仍默认OFF。小N逐矩阵VM compute改善约8%–39%，长generic仍有−0.86%/−2.53%负项；重复大图显式缓存改善约9.3%，不保证所有负载受益。完整构建后集中组合验收通过3份重编API控制、2份VM原C流、N10000真正串行默认、4096→10000→4096并行缓存流及2项失败清理；最大输出和混合流共约1.87GB逐字节真值通过。性能来自各自冻结候选，比例不相乘；当前版本单次规模验收不作配对提速声明。后续本地构建先重新运行local-mingw配置preset，旧objects不能证明新库。

已安装显式批量前端 `tools/analyze_batch.py` 和 `--skip-ir`。同一翻译单元六输出的严格批处理由12→3次Clang调用，三对测量配对中位减少70.15%；显式省略审计IR减少48.42%。168次原C对照及源/头文件变化和输出冲突控制通过；默认单次完整审计未证明提速。用法见[Metadata说明](docs/metadata.md)，性能与验收范围见[阶段指标](docs/stage-metrics-2026-10-13.md)。

2026-10-13 当前阶段：普通运行文件已更新为 `310aca276379...`，固定栈与只读指令引用使23组VM数据流计算时间全部下降，七对配对的逐流中位降幅中位数11.09%；400完整输出、13项CTest及4份新源码独立校验通过。前端默认Metadata改为LF换行，六源schema2总字节10,724→10,046（−6.32%），可用`--metadata-newlines native`恢复宿主换行；复用真实Clang driver版本使正常子进程3→2，18对分析耗时中位减少33.49%。原生候选与B128几何累计274次输出一致，但新Shape性能未稳定改善，保留AUTO默认。见[阶段指标](docs/stage-metrics-2026-10-13.md)与[机器记录](artifacts/project19-stage-metrics-2026-10-13.json)。以下2026-10-12及更早数字为历史冻结记录。

2026-10-12 第二轮：隔离`load-run4`候选支持无侧入口最多四条LOAD融合，原step/PC、逐条栈边界和异常顺序保留。GNU Release 16项CTest通过（融合合同8606次比较），19源首个小矩阵对原C完整字节一致；动态分派减少量1280，旧LOAD对同集1135。选取三组已使用数据流做5轮交替同二进制未融合/融合全进程配对，中位−2.83%、+9.91%、−3.45%，这不是与旧LOAD对的性能比较，收益不一致，未改默认。见[开发记录](../../docs/four-project-development-round2-2026-10-12.md)和[机器证据](../../outputs/four-project-development-round2-2026-10-12.json)。

2026-10-12 新增 `tools/profile_vm_dispatch.py`，在原Metadata上独立执行有界小矩阵跟踪，记录真实opcode/PC/bigram和无侧入口的LOAD对覆盖。19份原源码的首个小矩阵全与原C逐字节一致，源码/Metadata/输入/完整oracle哈希均核对；3项控制验证预算边界、跳转侧入口、三LOAD不重叠及循环频次。此批只解释动态覆盖，不测C++耗时、不改默认，后续需在同源性能输入上决定融合方向。见[动态覆盖](artifacts/dispatch-profile-verified-2026-10-12.json)。

当前普通 Release `99a87d135378...` 已接入验收后的 VM 默认后端：保持 native/AUTO 优先，真正需要 VM 的程序在 GNU 构建中默认使用 `decoded-threaded`，portable 回退到 `decoded-fallback`；显式 `--vm-backend legacy|decoded|decoded-threaded` 保留。实际普通安装通过8项合同及147份原C全文件复验，隔离 GNU/portable 各12项回归、378份原C对照。N10000 while-copy三个后端在明确1e10预算下逐字节通过，默认1e9仍明确拒绝1,700,000,012步；这不是默认预算的通用N10000通过。原4f73完整回滚与memory7da06保留，native数学、Metadata完整图、AUTO块规则和严格FP不变。见[当前VM默认集成](docs/stage2-vm-default-integration.md)及`artifacts/stage2-vm-default-integration/ordinary-install/release-manifest.json`。


当前生产默认99a与旧普通4f73已独立完成13源×5对、130次运行，原C全文件全部一致；65/65对compute更短，逐源配对中位减少52.16%..80.58%。每次为实际默认auto且真正需要VM，解码计入compute；原C缓存流沿用，旧EXE缺失步骤/解码字段不补填，IO/wall与宿主负载单列。这是本宿主VM范围的实际生产收益，不是native Cholesky或官方85分结论。全五比值、完整成本和来源见[生产默认配对记录](docs/stage2-vm-production-default-performance.md)。

另在独立研究构建中加入默认OFF的有限PROGRAM步数证明：`CHOL_PROVED_VM_BUDGET=ON` 后显式使用 `--vm-budget proved`，只对获证明的有限控制流选择有界预算；无法证明时仍保留1e9。它与任何显式 `--vm-step-limit` 互斥，native路径不做VM证明，Metadata完整图和PROGRAM均不改变。普通99a与memory7da06仍保留；469份完整原C输出、GNU15项回归及边界合同已通过。N10000完整while-copy的GNUauto/decoded/portable三个proved后端已逐字节通过，实际有限上界及步数均为1,700,000,012，未传显式limit；固定默认1e9仍按预期拒绝。这是获证明子集的可选策略通过，尚未推广普通默认或解决所有通用循环。规则与证据见[有限步数隔离接入](docs/stage2-vm-proved-budget-integration.md)。

官网：[题目详情](https://www.chaspark.com/#/races/competitions/1326691788365586432)，2026-10-10复核。

现有链路为 **实际C源码 → Clang AST/LLVM IR → 参数化符号循环、访存与可执行字节码Metadata → 动态Shape Runtime → 二进制结果 → 独立编译原始C源码逐字节比较**。算法分派来自完整运算图证明，变量名、函数名和源hash仅作追溯。

## 构建和运行

```powershell
.\scripts\bootstrap.ps1
.venv\Scripts\python.exe tools\analyze_source.py fixtures\official_naive_transcribed.c --function cholesky --output artifacts\quickstart-smallest.meta --smallest-metadata
build\cholesky_runtime.exe --metadata artifacts\quickstart-smallest.meta --input artifacts\synthetic-input.bin --output artifacts\quickstart-result.bin --scheduler parallel --threads 4
```

普通`build/cholesky_runtime.exe`接入schema 1/2/3读取器，能够直接执行`--smallest-metadata`选择的结果。前端默认仍schema 2，显式最小策略从schema 2/3 × dag/table/expanded/packed八种完整等价编码中按实际文件字节数选择。2026-10-14新增完整图packed编码与读取器优化；本轮主测试明确为朴素/左看/分块Cholesky，题面核对及本地契约见[题面记录](docs/task19-requirements-2026-10-14.md)，最新成果见[开发验收](docs/development-2026-10-14.md)。bootstrap会生成示例输入；完整原C测试可再运行`.\scripts\test.ps1 -Profile full -LargeShape 10000`。迁移机器需先配置下文工具链和Python环境。

本阶段保守配置保持`CHOL_PACKED_READY_KEYS=OFF`与原AUTO规则。B128仅作为显式可选参数`--tile-size 128`：在已测16线程fresh N6145/N8193及N10000复验中，compute中位改善约7.2%/7.7%/7.4%；范围仍有重叠且10000有一次反例，未修改AUTO或拟合新N阈值。详见[独立Shape验证](docs/stage2-grain128-holdout.md)。

旧默认`2b05...`和memory`7da0...`的实际EXE已在`artifacts/stage2-runtime-release/historical/`保存，并附原build-provenance与旧build路径映射。旧报告保持原记录，历史复验应使用冻结快照；普通build路径用于当前基座版本。当前Release验证与发布来源见该目录的新manifest，不把过去SHA对应的报告套到新二进制上。

另有默认OFF的完整Metadata压缩容器：`--compress-metadata`可与最小选择组合，要求独立`build-stage2-zlib`开启`CHOL_COMPRESSED_METADATA=ON`；普通发布仍不启用压缩容器。组合选项从一次AST/IR生成的六个完整容器按最终字节选最小；单独未压缩最小策略保留原规则。容器以随项目提供的官方zlib 1.3.2源码静态链接，压缩完整图/PROGRAM/依赖，严格拒绝损坏及超限流；六源最终文件为731/735/912/481/397/225字节。使用命令、候选全记录、边界、原C对照及完整成本见[Metadata压缩协议](docs/metadata.md#可选完整文件压缩容器)，不换算官方15分或声称计算加速。

默认`local-mingw`使用行主序输出与packed因子，提供保守吞吐配置。内存较紧时可显式构建第二配置，两个配置的测试输出互不覆盖：

```powershell
cmake --preset memory-mingw
cmake --build --preset memory-mingw --parallel 4
ctest --preset memory-mingw
build-memory\cholesky_runtime.exe --metadata artifacts\official-naive.meta --input artifacts\synthetic-input.bin --output artifacts\memory-result.bin --scheduler parallel --threads 4
```

memory配置只对实际结构分类失败、获证明的块图复用A；带状/对角成功路径仍需A+L，通用VM和stage也保持原分配。普通N10000峰值约1.22GB而默认约2.02GB，部分吞吐测试为负，不承诺通用加速。

需要本机CMake4.2、GCC15.2、Clang21.1、Python3.12标准库环境。预置工具链路径见 `CMakePresets.json` 与脚本PATH，迁移机器需调整。无需GPU/NPU；AVX2/FMA路径在基础指令集检测后启用，`--simd portable` 强制回退。

```powershell
$env:PATH='E:\mingw64\bin;C:\Program Files\LLVM\bin;'+$env:PATH
.venv\Scripts\python.exe tools\evaluate_source.py --source fixtures\cholesky_blocked.c --function cholesky_blocked --sizes 3,17,33,65 --blocks 1,7,32,100 --threads 1,2,4
.venv\Scripts\python.exe tools\analyze_source.py fixtures\official_naive_transcribed.c --function cholesky --output artifacts\official-naive.meta
build\cholesky_runtime.exe --metadata artifacts\official-naive.meta --input artifacts\synthetic-input.bin --output artifacts\result.bin --scheduler parallel --threads 4
```

`--engine auto|vm|stage|tiled` 分别选择自动策略、真实源码VM、旧列阶段池与块任务DAG。`--block-size` 是分块源码的第四参数，`--tile-size` 独立控制物理调度块。`--ready-queue heap|bucket` 提供两种依赖就绪队列，heap为默认；bucket仍属实验选项。`--vm-step-limit` 默认10亿，未证明的源保持串行控制流。

## 已实现

| 部分 | 能力 |
|---|---|
| 前端 | 类型化Clang AST、int32/double、直接数组、for/while/if、条件与短路、算术比较、sqrt/fabs/fmin/fmax/显式fma、纯标量SSA helper |
| Metadata | Shape与源码block参数槽、循环与访存归属、共享符号表达式DAG和可执行程序；省去无参数操作码的冗余0；体积与N无关 |
| 证明 | 左看、官网右看及连续动态分块的完整运算图；支持变量改名、合法步进/等价边界/整数地址交换；不重排浮点式 |
| 块Runtime | 参数化POTRF/TRSM/UPDATE DAG、8字节任务、闭式后继、每矩阵持续线程池、packed因子缓存、奇数/尾块 |
| 数值 | 每位置源列递增链保持；禁隐式FMA与fast-math；显式fma独立路径；portable与CPU检测AVX2互验 |
| VM | 源变化对应实际程序变化；整数转换/除余与溢出检查；不证明的算式执行VM |
| IO | 小端uint32 M、每矩阵uint32 N和行优先FP64；逐矩阵流式处理；失败不发布结果，清理.partial |
| 计时 | compute含分配/图/调度，图和kernel另列；Metadata/输入/输出IO与进程wall分别记录 |

## 测试和研究证据

13种源覆盖实际官网转录、朴素/分块、改名/循环变体、改变算式、SSA helper、整数转换与通用控制流。`tools/test_project.py` 同时对照原始C oracle、VM、自动/块路径及重复并行。上一阶段冻结的两配置CTest均7/7（默认159.28s、memory199.42s）；各full基础流水线188次比较/24拒绝、helper49/17、while63、整数选择105/12，总计各405比较/53拒绝。独立结果在 `artifacts/build-ctest-*` 和 `artifacts/build-memory-ctest-*`，原生所有权及308880扫描位/保护页单测另计。历史4f73基座另通过8/8 CTest（110.40秒）和wire/min全文件验证，来源仍在`artifacts/stage2-runtime-release/`；当前普通发布验收见本文开头的新manifest。

| 独立里程碑 | FP/边界或编码对照 | 稠密性能执行 | 证据JSON |
|---|---:|---:|---|
| 块DAG与打包 | 60 | 240 | `artifacts/tile-milestone/tile-report.json` |
| 紧凑图与最大规模 | 96 | 62 | `artifacts/extended-milestone/extended-report.json` |
| 4/8/16独立累加器 | 128 | 180 | `artifacts/microkernel-milestone/microkernel-report.json` |
| CPU检测AVX2 | 128 | 112 | `artifacts/simd-milestone/simd-report.json` |
| 对角因子缓存 | 128 | 176 | `artifacts/panel-milestone/panel-report.json` |
| 对齐与就绪队列 | 136 | 264 | `artifacts/ready-milestone/ready-report.json` |
| Metadata等价编码 | 24 | — | `artifacts/metadata-milestone/metadata-report.json` |
| 两行与唤醒 | 128 | 252 | `artifacts/row-milestone/row-report.json` |
| 四行 SIMD | 128 | 168 | `artifacts/row4-milestone/row4-report.json` |
| 中等 Shape 成本 | — | 200 | `artifacts/shape-cost-milestone/shape-cost-report.json` |
| helper求值/类型 | 49（另17拒绝） | — | `artifacts/helper-type-milestone/helper-report.json` |
| 带状/新稠密族 | 380 | 46（含结构化） | `artifacts/structured-milestone/structured-report.json` |
| 线程/Shape分派 | 38 | — | `artifacts/shape-final-milestone/shape-final-report.json` |
| 八行实验（负收益） | 128 | 128 | `artifacts/row8-milestone/row8-report.json` |
| 4/8/16线程与RAM | — | 48 | `artifacts/scaling-milestone/scaling-report.json` |
| 线程/块几何成本 | — | 81 | `artifacts/thread-geometry-milestone/thread-geometry-report.json` |
| 计数型while证明 | 63 | — | `artifacts/while-block-milestone/while-report.json` |
| P/T内独立位置SIMD | 128 | 200 | `artifacts/vector-panel-milestone/vector-panel-report.json` |
| 完整线程策略 | 144 | 116 | `artifacts/thread-policy-milestone/thread-policy-report.json` |
| 有界通知实验 | 208 | 156 | `artifacts/bounded-notify-milestone/bounded-notify-report.json` |
| 缓存清零/锁外通知实验 | 208 | 66 | `artifacts/lazy-pack-milestone/lazy-pack-{stress,performance}-report.json` |
| 连续列块工作区（负结果保留） | 209 | 94 | `artifacts/column-workspace-milestone/column-workspace-{stress,performance}-report.json` |
| 混合块布局/并行导出 | 418 | 188 | `artifacts/row-tile-milestone/row-tile-{stress,performance}-report.json` |
| 当前panel惰性图 | 418（另30异常退出） | 104 | `artifacts/lazy-graph-milestone/lazy-graph-{stress,performance}-report.json` |
| 当前等待/因子行前缀 | 418（另30异常退出） | 156 | `artifacts/lazy-prefix-milestone/lazy-prefix-{stress,performance}-report.json` |
| 单worker闭式拓扑遍历 | 642（另30异常退出） | 76 | `artifacts/serial-walk-milestone/serial-walk-{stress,performance}-report.json` |
| 同源向量扫描 | 545（另288非有限拒绝、308880单测） | 60（含带状） | `artifacts/vector-scans-milestone/scan-{stress,performance}-report.json` |
| 输入所有权复用 | 518（另36失败/API单测） | 80 | `artifacts/input-reuse-milestone/input-reuse-{stress,performance}-report.json` |
| auto输入复用/最终配置 | 854（另288拒绝/42失败） | 74 | `artifacts/input-reuse-auto-milestone/auto-{stress,performance}-report.json` |
| 纯int选择器helper | 105 | — | `artifacts/integer-selector-milestone/integer-selector-report.json`（另12拒绝） |

一般稠密 **N10000已经实际运行**：原始C oracle约504.670秒，完整800,000,008字节结果严格相同；单次CPU AVX2 B64、4线程compute约4.192秒。后续批次存在并发负载波动，完整区间与同批对照见JSON；不把不同批最快观测串联成稳定加速比。N2048对角因子缓存同批5轮B64/4线程中位86.592→36.443ms，N4096为452.281→227.748ms，但N10000该批并未稳定改善。

`-LargeShape 10000` 使用完整800MB布局的**对角SPD**与独立解析真值，证明最大Shape、IO及实际数据检查后的结构专门化；它不是普通稠密性能。普通稠密的长基准见 `tools/benchmark_extended.py`、`benchmark_simd.py`、`benchmark_panels.py`、`benchmark_ready.py`。研究工具使用 `research_reference.py` 校验source/input/oracle SHA后复用原始C参考；大文件缺失时自动重新生成和编译原始C，最大参考可能耗时约8分钟。

Metadata左看/官网右看/自设分块为2250/2655/3739字节，展开编码相对减少16.0%/19.1%/15.9%；来源SHA和完整符号图保留于 `.analysis.json`。`--symbolic-format expanded`、`--provenance-inline` 可选审计模式；`--full-bytecode-args` 供较旧v2读取器使用。

最终配置根据实际worker数选择B：单线程N<=1536用32，多线程N<=1024用32，其他64。AVX2在N>=2048用四行×八列，否则两行×十六列；八行实验性能负面，未选默认。helper重复SSA按槽线性求值，前向prototype及同函数嵌套支持；未使用或整数求值未获证明的helper保守留VM，float/unsigned/wide返回与错误数学签名拒绝。可证明的声明+底部单位递增while按真实循环语义认定，不改写原VM程序。

默认实际扫描数据的确切半带宽w，w<=128且4w<N时可以结构专门化，`--structure dense`关闭，`--band-limit`覆盖上限。带内实际零仍参与k链，带外符号零保留。N10000带宽7真正运行原始C oracle约481.611秒，三轮compute中位旧dense内核3002.110→带状184.861ms；它是结构化成果，不是普通稠密速度。当前带状kernel串行，metrics报告实际worker1。

线程扩展批次固定B64的普通N10000，4/8/16线程三轮compute中位2535.090/1801.070/1630.260ms，实际进程峰值工作集约1924.5MiB。M3=[4096,10000,4096]完整1.068GB结果逐字节相同，峰值仍约1924.7MiB，符合逐矩阵流式；其8/16时间存在重叠和负观测。Win32峰值工作集与commit、宿主可用RAM20ms采样分开记录；宿主共享负载/温度未隔离，不能当官方预测。

完整线程研究候选在B>=64才向量化P/T独立位置，8/16线程且N>=4096自动B96；其余小块阈值保留。144 FP压力＋116性能均保持原C字节。4096单线程715.265→627.143ms、4线程221.434→189.402ms；10000的16线程1648.560→1368.370ms，但8线程1664.370→1700.280ms为负，M3的4线程也负。该批宿主最小可用RAM仅3.576GiB，保留长尾及反例，不能宣称全局最优。惰性任务状态O(t²)、缓存等待/行前缀已有418+30严格验证，各104/156性能批保留负结果，两个选项暂OFF。历史ca0与后续构建数学kernel同序，但混合布局添加的SIMD logical_size参数保留在后续ABI，因此这些是整版本对照，不宣称调度单因素因果。最终双配置选择见构建章节；历史可复現工具 `benchmark_thread_policy.py --mode policy` 使用冻结二进制。

单worker闭式遍历删除常驻状态/队列，但普通10000三轮单线程compute中位旧9463.690/候选10204.800ms为负，保持OFF。向量扫描用整数FP64位模式判断有限值及首个非零，545原C对照、288拒绝及保护页单测通过；同源带状10000 auto compute167.145→147.255ms，ordinary dense单线程仍负9482.680→9570.510ms。完整负结果保留，输入校验计入compute并另列input_validation_ms。

所有权复用研究候选对同源hybrid布局只改输入生命周期，518严格C比较及36失败通过；普通10000 t4峰值工作集2,017,865,728→1,217,859,584字节，M3也约1.22GB。t4 compute中位3295.490→2930.670ms，但export33.506→57.043ms，单轮仍负。`execute_owned`消费A并在所有worker退出后交换到L，upper显式+0；const `execute`保持输入不变。auto扩展已独立完成854 C对照、288拒绝/42失败、74性能，结构成功仍分配完整L而结构失败可复用A。明确吞吐负值：普通10k单线程row9194.470/memory12984.300ms，M3t4 3256.665/7129.730ms；不保证全局更快。最终`local-mingw`为保守row，显式`memory-mingw`提供约800MB峰值节省，CMake普通选项默认OFF。owned输入析构计入compute，历史const时间不直接横比。

单个N10000需A+L约1.6GB、打包约400MB，再加图和队列；比较时输入/参考/输出约2.4GB磁盘，建议16GB RAM和至少4GB测试磁盘。大文件成功核验后可删除，manifest与JSON保留来源/字节/SHA/计时；历史二进制SHA单独保存。最终两配置各在普通dense10000、真正band10000w7、M3再做完整参考核对，6次全部通过（46.277s），不重算昂贵C oracle；单次band memory1041.010ms/default187.096ms负值保留，不能当稳定比较。构建/源码/preset/二进制SHA见 `artifacts/final-profiles/build-provenance.json`，scale证据见同目录`scale-report.json`。native源码和两套配置已冻结。

中文版单文件研究报告为 `reports/project19-research.tex`，包含重要研究、算法、同批成果、资源与时间成本。

一般VM优化第一阶段已实现可选参数预解码，默认OFF；原栈/switch、33opcode步骤和报错顺序保持，普通4f73仍冻结。404条边界对照、172份实际原C完整文件、7类旧版错误合同及9/9项目回归通过，另有显式fma/负零/subnormal实际C验证。N10000一般while-copy的四份800MB结果与真实原C全字节一致，实际原步骤1,700,000,012，使用显式1e10预算而没有放宽默认1e9。90条同EXE配对、9类真正依赖VM的源，在背景负载下配对中位compute下降2.36%..18.79%，45对中2对慢2.40%/2.56%保留；没有推定官方得分或晋升默认。完整比值、成本/资源和冻结版本见 [VM第一阶段记录](docs/stage2-prepared-vm-phase1.md)。

第二阶段可选双栈顶缓存已完成290次全C字节、480项指令合同和100,000次NaN/负零payload对照，10/10回归通过；12类程序同候选120次配对全部60对为负，paired中位慢11.89%..26.29%，包含2新源和新shape，保持OFF且不替换第一阶段。完整负结果、来源和限制见 [VM第二阶段记录](docs/stage2-prepared-vm-phase2.md)。

第三阶段冻结研究（当时默认OFF）：可选 GNU labels 直接分派保持普通 vector 栈、完整 PROGRAM 和每原 opcode 的计步/错误顺序；`CHOL_THREADED_VM` 默认 OFF，启用后仍默认 legacy。GNU 与实际强制 switch 回退分别通过 934 条契约，Clang UBSan 同样通过；13 源 378 份原 C 完整输出及 7 类错误一致，11/11 CTest 通过。编译器实际只保留 3 个分派站点并自动 inline 原 pop，不能单独归因分支；同一候选 130 次配对完整保留，65/65 对 compute 为正，13 类程序 paired 中位减少 47.67%..60.34%，包含一项新源/新形状；这是本宿主负载下 VM 范围结果，默认仍 OFF。详见 [VM第三阶段记录](docs/stage2-prepared-vm-phase3.md)。

## 新阶段：文献、就绪队列与Metadata

2026-10-11先核对PLASMA/LAPACK、StarPU和2026年的Cholesky-Bench原论文，再开展独立优化。经典BLAS的数学等价不足以保证原C逐字节结果；本阶段仍保留每个位置的FP64运算顺序。[研究记录](artifacts/stage2-packed-ready/research-and-plan.json)包含迁移判断和预声明队列计划，此前最终报告属于上一阶段冻结记录。

新就绪队列将不可变列/面板/节点优先级缓存到64位键，`CHOL_PACKED_READY_KEYS`默认OFF，原heap顺序和8字节队列项保持。候选7/7 CTest通过（252.19秒）；30次交替原C全文件配对均一致。普通10000四线程中位compute约3883.59→3614.03ms（−6.9%），但2048四线程和10000十六线程约+1.8%/+1.7%，区间重叠，不推广为默认或声称普遍加速。见[配对记录](artifacts/stage2-packed-ready/performance.json)。

新增可选`--symbolic-format table`将符号记录的重复字段名存一次，显式presence mask区分字段缺失与null，保留完整表达式DAG、全部符号访存记录及原始字节码。三种源码Metadata分别2250→2036、2655→2325、3739→3289字节（减少9.5%/12.4%/12.0%）。400个稀疏记录往返及12个实际原C/VM/tiled全文件对照通过，重建图和字节码一致，22.04秒。属于Metadata字节优化，不换算15分或计算加速；默认dag保持。见[表编码验证](artifacts/stage2-metadata-tables/report.json)，解码在`tools/symbolic_metadata.py`。

## 明确的本地契约

新增隔离的 AVX-512F 研究构建，默认 `CHOL_BUILD_AVX512_KERNEL=OFF`，历史已验收 4f73 与 memory 二进制冻结；auto 仍为原 AVX2/portable 路径。240 次实际 C 全文件对照、16 个 IEEE754 位 golden、1400 个保护页组合和 9/9 CTest 已通过。60 次同二进制/同几何交替性能均保持原 C 全字节，N8193 中位约−4%至−6%，但 N6145 B128 约+22.75%，N10000 中位变化不足1%，30对中11对负面；不推广默认。显式 `--simd avx512` 的 CPU/OS gate、重建命令、完整范围和预声明见 [AVX-512 研究说明](docs/stage2-avx512.md)。

本阶段新增显式选择的`--metadata-schema 3`（与`--symbolic-format table`可组合），用固定33 opcode单字符ID保留原参数文本、字节码顺序和完整符号图；默认仍为schema 2。新`build-stage2-wire`兼容v1/v2，旧Runtime应拒绝v3。左看/官网右看/自设分块从2250/2655/3739降为1719/1934/2626字节（约23.6%/27.2%/29.8%）。33项独立golden、29项原生错误编码拒绝及60次五种原C全文件对照通过，包括负零、通用控制流与VM/tiled。小程序有固定字段开销，不保证都缩小；不换算正式Metadata 15分。协议定义见[Metadata文档](docs/metadata.md)，完整SHA与对照见[wire验证](artifacts/stage2-metadata-wire/report.json)。此能力已通过新增验证安装到普通build；历史默认EXE及旧研究报告保存冻结。

实际保留的负结果：`noop`常量返回源的v2 dag/table为306/338字节，v3 dag/table为324/356字节，新增encoding字段未被两条指令摊销，增加18字节；四个版本的原C完整字节均通过。见[固定开销反例](artifacts/stage2-metadata-wire-overhead/report.json)。

可选`--smallest-metadata`在一次AST/LLVM IR编译后，从schema 2/3 × dag/table/expanded六种完整等价编码选出文件最小者；平局优先schema 2，再优先dag/table/expanded。它与显式`--metadata-schema`、`--symbolic-format`、`--full-bytecode-args`互斥，需新Runtime；默认选择不变。六种实源对每个显式候选验证完整图/PROGRAM/依赖相等，所选文件均不大于旧默认，24次VM/tiled原C全文件对照通过（65.20秒）。左看/官网右看/分块仍选1719/1934/2626；负零小源选v3 dag 619（原667），noop选v2 expanded 284（原306），避免固定头开销反例。见[最小文件策略验证](artifacts/stage2-smallest-metadata/report.json)。

独立新wire构建8/8 CTest通过，原source流水线仍405个全文件字节比较/53个拒绝，160.93秒；schema 3的60次比较单列，未把旧schema 2流水线当作schema 3验证。额外12个原生IEEE754解析bit golden覆盖正负零、最小subnormal、最小normal、最大有限数和2^53边界，并对两个schema核验；14次VM完整输出比特检查另存独立记录。当前wire二进制SHA及对应前端版本见各新验证目录。

最小策略重组前端渲染后，又对刚完成四类full流水线中全部46个Clang已接受源码校验原source SHA，重新生成默认Metadata；46个文件与原产物逐字节相同，无跳过（60.64秒）。覆盖helper、while、整数选择器及随后在执行阶段拒绝的整数未定义行为程序；此项验证默认输出回归，不重新执行原C oracle。见[默认Metadata完整字节审计](artifacts/stage2-default-metadata-audit/report.json)。

官网图 `1326692271903821824.png` 的主体已目视核对，未给helper定义或L初始化。本地 `div(x,y)=x/y`、`madd(x,y,z)=x*y+z` 非融合，L全+0；显式fma另测。`fixtures/cholesky_blocked.c` 是自设合法分块，不冒充官方源。输入为有限SPD且源码计算的pivot保持有限正值，默认最近舍入、常规subnormal处理，不改FTZ/DAZ。

前端支持上述明确C子集，未支持任意C、指针别名、二维VLA、堆分配、mutable/control-flow helper；不支持构造拒绝。整数未定义行为检测拒绝，不运行C oracle制造真值。Metadata是受信编译器与Runtime的本地接口，不声称官方格式；分数仅报告原始字节与时间，没有归一化官方得分或隐藏评测通过结论。下一阶段和资源要求见 `docs/development-plan.md`。
