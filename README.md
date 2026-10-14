# 2026 Hackathon 四赛题开发工作区

2026-10-12 第二轮开发完成：[开发记录](docs/four-project-development-round2-2026-10-12.md)。11完成两批真实3B NF4成对测试，共16次生成，公开和离线均0通过；公开修复仍无质量收益，54单元测试中53通过、1跳过。18七个已筛选图COPY331→324，三个图改善，327份完整输出和77046标签独立重放通过；更大预算、不改全336结论。19最多四LOAD融合通过GNU16项CTest及19源原C小矩阵字节对照，三组计时两降一升，未推广默认。27前缀剪枝通过98个独立金标及8预算控制，原12仍4成功/8失败、0新增恢复。机器证据见[第二轮清单](outputs/four-project-development-round2-2026-10-12.json)。以下为旧批次记录。

2026-10-12 新评估与开发：用户本轮要求继续四题，11 已恢复开发。完整五维评估见[四赛题进度评估](docs/four-project-assessment-2026-10-12.md)。11 新增正式源码中的可选公开契约候选执行流程，4项新测试通过，尚无新模型质量结果。18 原336图新实验7图改善，COPY192859→192848、合法272图等权COPY/输出13.5636%，64无输出保留；867份完整输出与205911个不可变标签独立重放通过。19 新增原PROGRAM小矩阵动态跟踪，19源均对原C逐字节通过，覆盖不代表加速。27 新增有预算的原DIRECT边必要显存证书分析，4项控制通过，检查原12图的24个实际保存状态；诊断不算恢复。详见[本轮证据](outputs/four-project-continuation-2026-10-12.json)。下面为此前批次的历史进度，旧暂停和停止条件已由本轮指令替代。

最新增量：11题保持暂停。18题原336例独立核验保持：23图改善，COPY192902→192859，合法272图COPY/输出均值13.5842%；64个缺少输出的状态保留，全336均值未定义，Level1–3尚未证明。新静态归因已逐原身份核对全部272输出和4680候选：98个候选改善、2893相同、1689更差；新移动节点与固定指令序列交错的完整手工45例能13→0 COPY，944个连续≤32区域均受最小12槽间隔阻碍，证明旧邻域覆盖有限，尚未运行新求解。[归因与手工证明](outputs/stage2-root-mobile-backbone-hand-r190.json)。19题LOAD+LOAD隔离实现已实际通过GNU14、便携14、关闭13项CTest，新8464合同各GNU/便携通过，旧934合同各三构建通过；7项CLI全核验，3482文件验收冻结已独立检查。原测试脚本计数写错的首次失败保留，历史真实C pipeline覆盖默认auto兼容，显式融合真实C目前只有N3 CLI，尚无加速证明。[功能与冻结核验](outputs/stage2-root-load-pair-actual.json)。27题GCC与Clang UBSan各160金标、16预算边界控制通过，634次原DAG完整计划物理重放一致；每套人工helper136成功/24未完成。随后原12例实际仍4成功、8失败，0恢复、0丢失；8个完整helper/whole计划经独立堆重放一致，收费相对R51增加2.32%，该方向保留为负结果，未扩63全图或推广默认。[原12例独立核验](outputs/stage2-root-causal-selected12-actual-r56.json)。旧报告和各批历史证据保留。

新阶段已按用户指令继续推进：11题现按用户要求暂停，保留代码、模型与结果；18研究Level1–3可达性，19/27按题面进一步优化。先检索经典及2025–2026主论文，再实现和独立验证。下文35%停止与91页报告是上一阶段完成记录，新阶段不沿用该停止门槛。增量见[工作记录](outputs/stage2-progress.json)，旧报告与原始结果保留。

11、18、19、27已配置环境、搭建框架并完成实际可运行的自建测试、研究优化与报告。34题分析保留，第18题补充要求已同步，10月11日再次读取官网仍未明确Level2及COPY平均口径。上一阶段在北京时间2026-10-11 06:30按35%额度条件停止；用户后续指令已启动新阶段。下表列当前已验证结果，各批来源与SHA见工作记录。

| 项目 | 当前实现与测试 | 开发计划 |
|---|---|---|
| [11 上下文治理](projects/11-context-governance/README.md) | 按用户要求暂停，相关代理和模型测试进程已停止；代码、下载权重和历史结果保留。完整正确性仍未证明 | [计划](projects/11-context-governance/docs/development-plan.md) |
| [18 ISA调度](projects/18-isa-scheduler/README.md) | 最新336区域候选：272合法、47模型证书、17失败保留；23图改善，COPY192902→192859，合法子集COPY/输出均值13.5842%。5116份完整输出与711769路径标签独立核验通过。全336质量均值未定义，Level1–3尚未证明；默认auto不变，隔离实现移动节点与固定指令序列交错的新邻域 | [计划](projects/18-isa-scheduler/docs/development-plan.md) |
| [19 动态图](projects/19-dynamic-graph/README.md) | 普通默认为99a：13源65交替配对均较旧4f73更快，各源计算中位耗时减少52.16–80.58%，原完整C逐字节一致；原native/AUTO和便携回退保持。新有证明的预算策略已在隔离构建中通过469份完整C输出、49个原错误对照、15项GNU回归、便携/关闭构建合同及UBSan。N10000的三个后端均在未传显式上限时，按实际PROGRAM推导17亿步预算并执行全部1,700,000,012步；三个800000008字节输出和原C参考已独立流式全比对。固定10亿步模式仍拒绝。该策略尚未成为普通默认，继续评估证明成本及嵌套循环扩展；有限C子集结果不证明任意C支持或正式成绩 | [计划](projects/19-dynamic-graph/docs/development-plan.md) |
| [27 多流调度](projects/27-aicore-streams/README.md) | R51已更新为实际默认：困难集145/202合法，新48保持42/48；63个已知可行图仍未解。1099回归、625固定数值控制、102释放切分控制已验收；实际默认14回归及10代表案例通过核对，7个合法计划独立堆内存重放，3个失败明确保留。成本使用另一份同源Release程序：12次运行共1500记录，1119个实际完整计划独立重放；三轮配对CPU中位困难集−6.24%（第三轮+6.07%）、新48−2.90%且墙时+0.46%，宿主负载与内存采样保留，不称稳定通用加速。完整R48回退及用户打开的历史TeX保留 | [计划](projects/27-aicore-streams/DEVELOPMENT_PLAN.md) |

```powershell
cd F:\Hackathon
# 11暂停期间，仅运行18/19/27完整CPU测试，含N10000格式/结构化SPD
.\scripts\test-all.ps1 -Full -MaxShape -SkipProject11
```

19题的预算证明成本对照也已独立验收：同一隔离程序共114份完整C输出、57组交替配对，45组VM配对中34组耗时增加；两个短任务中位耗时增加82.1%和126.9%，证明自身分别约0.111和0.144毫秒。4个native对照均未执行证明，计时仍有波动。全部负结果、宿主负载及资源门槛保留，因此普通默认仍为固定预算，继续研究嵌套循环证明。详见[成本证据](projects/19-dynamic-graph/artifacts/stage2-vm-proved-budget/policy-cost/final-evidence/summary.md)。

27题的最终存活内存筛选，修订后176例通过独立核验，初次7个随机夹具资格失败完整保留。随后已覆盖全部剩余63图加4个既有恢复控制：63图均未恢复，4个控制的完整计划及T/peak相同，8个实际helper/whole计划独立堆重放通过。总逻辑工作量636931404→637093426，16例增加、11例减少、40例相同；这是工作计数，CPU性能未测。该单项筛选停止继续扩测，保持隔离，默认R51不变，转向能够改变调度顺序的方案。详见[67图负结果报告](projects/27-aicore-streams/reports/research-batch54.md)。

18题的[固定权重AWA*](projects/18-isa-scheduler/research/level-stage/tree-pair-anytime-plan.md)先在原40个小图上达到已知固定交错范围的最优结果，再完成同原84例。全部526036条路径标签、15560个待搜索状态和44个未完成扩展的物理年龄已独立重放一致；这批实际覆盖了48760次状态重开和908次过期队列项。搜索耗时与诊断导出、写盘、验证单列，共享功能测试时间不能用于加速结论。相对旧DP的单例退化原样保留，官方Level1–3仍未证明。

18题的单例退化已追溯到wrapper：一个pair达到16出口后误终止整个输入。修订版继续下一pair并保留整体partial，共用原500毫秒/20k预算。随后完整336测试及独立核验通过：272合法、47模型证书、9预算失败、8调度失败均保留；18图改善，总COPY192929→192902。837份完成提案与基线、最终输出共1381次独立物理重放，386672个路径标签、18088个OPEN和65个未完成扩展逐个核验。合法272图COPY/输出均值13.7147%；缺少输出的64图使全336质量均值仍未定义，不能称通过Level1。25次搜索均为partial，下一步分析剩余COPY及覆盖后设计更强算法。详见[完整结果](projects/18-isa-scheduler/experiments/r178-anytime-full336/report.json)与[独立核验](outputs/stage2-root-tree-pair-full336.json)，默认未变。

19题的嵌套循环证明组件已通过独立重编译：1081例金标、2162个预算边界、16320个单点变异（872个返回证明）、220个未知控制与4个提前退出/错误组通过，共4995次原legacy VM执行未超过证明上界。可选Runtime接入已完成四套匹配新ABI的隔离构建；小型CTest分别13/13、13/13、12/12、10/10通过。四个后端选择程序独立重跑190项观察、15项剩余预算检查、60次固定预算边界执行一致。两阶段证明共用250k工作预算，既有证明成功时跳过嵌套证明。后续624份完整C比较、56错误、10CLI及完整回归/UBSan已经完成，最终独立验收见下文。详见[独立合同核验](outputs/stage2-root-vm-nested-runtime-contracts.json)。任意C支持仍未证明，普通默认保持固定预算。

27题的隔离失败切分分支搜索已完成小型验证：GCC和Clang UBSan各160个普通控制、16个直接routine控制及160个固定计划检查通过，264份实际合法cut顺序独立原图内存重放通过。原12图实际对照也已独立核验：仍为4图成功、8图未解，0恢复、0丢失，全部8个实际helper/whole完整计划、T、peak保持相同。逻辑工作54717560→60829525（+11.17%），不是CPU计时。该局部修复保持隔离，冻结负结果，转向真实失败前缀与切分覆盖的静态归因；不继续扩测63图或推广默认。详见[12图独立核验](outputs/stage2-root-frontier-selected12-r55.json)。默认R51和历史TeX保留。

19题完整功能批次首次退出码1的测试runner分类错误保留原样；修订runner按实际budget模式分类，复用已核验586次执行并补跑缺少38次，最终624份C输出逐字节独立核验通过，56错误和10CLI一致。完整CTest17/13/12/10及四个独立UBSan合同程序通过，2054份源码、构建、原始日志文件冻结并独立核对。可选嵌套循环接入在21源、24种Shape范围内验收，普通默认未改；当前没有该接入的性能收益或最大Shape结论。详见[最终独立验收](outputs/stage2-root-vm-nested-runtime-acceptance.json)。

18题通用DAG区域搜索的10项合同测试通过。固定80个N5–9小图及手工11节点图首次实际运行完成：81份均合法，8份实际搜索改善，总COPY24→0，手工图3→0；73份初始已无COPY不作为搜索质量证据。239份完整输出及184个标签已由根独立物理、寄存器读写顺序、符号与本地整数重放；oracle67最优、13预算未知、1超规模明确保留。下一步准备原336全部输入上的研究范围；尚未证明Level达标。详见[首次实际独立核验](outputs/stage2-root-general-region-actual-r185.json)。

19题新接入已完成25项高N纯证明分析，15项正例上界和10项未知控制符合预声明；未执行大矩阵。成本批174份完整输出共495920904字节与原C逐字节一致，87组同程序交替对照中73组变慢，其中VM69组有63组变慢。native18组不运行证明，仍有10组负波动，不把其噪声归因于证明。259份证明分析证据及672份成本源码、构建、日志已独立冻结核对，固定预算普通默认保持。下一步准备N10000三角程序完整运行验证及真正的指令执行优化。详见[证明分析核验](outputs/stage2-root-vm-nested-analysis-actual.json)和[完整成本核验](outputs/stage2-root-vm-nested-cost-actual.json)。

27题同12例的1011条保存前缀已独立重放：两例失败前缀导致后续原节点必要同时持有显存分别2469>2450、1656>1547；22个保存probe均未发现一个外部动作即可打开cut的情况。12份完整原图手工计划7合法、5预期拒绝，支持准备一次按原输入推导的因果输出延迟重启。当前仅授权隔离源码和160例预声明金标准备，尚无新恢复结果。详见[独立归因](outputs/stage2-root-causal-attribution-r56.json)和[设计核验](outputs/stage2-root-causal-plan-r56.json)。

18题下一方案已进入隔离实现：在最多32个连续原节点内，允许所有满足原数据及RAW/WAR/WAW依赖的ready节点重排，保留真实身份年龄和固定前后缀。手工完整11节点共享GET示例的3→1COPY已独立核验，但不是新算法的实测收益。前述自建合法272图的必要COPY下界为10.285%，只适用于该等权、只重排/COPY的测试模型，不能映射为官方成绩或借换分母宣布Level通过。详见[方案核验](outputs/stage2-root-general-region-plan-r180.json)。

2026-10-10完整统一脚本实际通过，其历史记录保留在`outputs/project-validation/`。10月11日各项目研究批次另行执行，不冒称统一脚本已经复验最新源码。11仍有错误生成；18与27有界搜索不能保证解出全部隐藏有解图；19严格数值对照只适用于已支持并验证的C子集。所有数据自行设置，不是正式成绩。

上一阶段四份独立中文TeX报告包含文献、算法、成果与负结果、资源成本和后续工作量：[11](projects/11-context-governance/reports/project11-research.tex)、[18](projects/18-isa-scheduler/reports/project18-research.tex)、[19](projects/19-dynamic-graph/reports/project19-research.tex)、[27](projects/27-aicore-streams/reports/project27-research.tex)。历史PDF共91页，两次编译及逐页视觉检查记录见[交付清单](outputs/research-delivery-manifest.json)。续研报告：[18 Level研究](projects/18-isa-scheduler/reports/project18-level-research.tex)、[18共享归约年龄搜索](projects/18-isa-scheduler/reports/project18-age-research.tex)、[27调度研究](projects/27-aicore-streams/reports/project27-research-resumed.tex)；旧报告保持原版。

新增[18子树交错研究报告](projects/18-isa-scheduler/reports/project18-subtree-research.tex)（4页，内置编译通过，独立原图金标与预算中断结果均保留）。

[详细测试报告](docs/test-readiness.md) · [环境与资源](docs/environment.md) · [后续开发统筹](docs/development-roadmap.md) · [官网更新](docs/requirements-update-2026-10-10.md)

原34题：[可搜索网页](outputs/2026-hackathon-review/赛题技术分析.html) · [Excel技术与资源](outputs/2026-hackathon-review/赛题与资源清单.xlsx)。

