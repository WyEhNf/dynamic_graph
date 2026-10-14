# 18号赛题：下一代 ISA 设计中的指令调度寻优

2026-10-13优化入口已接通：`python -m isa_scheduler.refine input.json --incumbent old-output.json --output improved.json --time-budget-ms 500`。它接收普通输出中的`stats.original_order`或研究候选包，逐步采用降低COPY的完整计划，并重新验证原身份、寄存器访问顺序及符号语义；省略`--incumbent`时先建立`age_portfolio`基线。500ms是追加优化预算，初始调度与最终验证另计。原`auto`与74份历史冻结源码保持不变。

R198完整336同上限对照已完成：两侧从相同的最新272合法输出（192841 COPY）出发，500ms/20000状态/20000转移；原移动邻域剩余1图改善至192840，新截断邻域30图改善至192801。合法272等权COPY/输出由13.5489%降至13.4824%；64个原无输出状态保留，全336均值仍未定义。新侧923份完整候选及全部物理前沿已独立核验，实际搜索51.83秒、完整输出核验37.89秒、前沿导出与重放101.02秒，不能将相同预算上限称为相同实际开销。证据在`G:/Hackathon-stage2-artifacts/project18/r198-balanced-mobile-full336-20261013/report.json`。

本轮进一步实现位集合成员查询、按固定骨架跨度分配预算、在线采用完整改善，以及未来固定消费者的COPY下界。29项针对性测试通过；其中位集合引擎在80个小图固定工作预算下，完整候选、物理标签及最终结果与原引擎逐项一致，COPY下界在240个小型受限邻域与不剪枝穷尽搜索最佳值一致。新策略均保留最好的已验证输出；受限搜索不能证明整图无解或全局最优。

2026-10-12 第二轮R197：新增`scripts/research_composed_mobile.py`，从R196七个已改善图的已验证输出继续有界搜索，严格改善后才采用新incumbent。COPY331→324，3图改善。完整输出327份（含310候选）、77046标签、2998 OPEN和21未完成扩展第二次独立重放通过。此为筛选DEV及更大预算（总1000ms/40000状态/40000转移、每轮最多500ms/20000），检查/导出另计，不改全336均值、64无输出状态或官方Level结论。见[独立核验](../../outputs/composed-mobile-selected7-audit-2026-10-12.json)及[开发记录](../../docs/four-project-development-round2-2026-10-12.md)。

2026-10-12 原336图移动节点/固定骨架实验完成：7图改善，COPY192859→192848，合法272图等权COPY/输出均值13.5842%→13.5636%，原64无输出状态保留，全336质量均值仍未定义。431个实际完整候选、基线与最终计划共867份，以及205911个不可变标签、2161个OPEN和26个未完成扩展，经另一次原身份、物理环与符号/整数重放核验通过。4项新深链/身份/顺序/SET槽解释器控制通过。默认未改，Level1–3未证明。见[完整实验](experiments/r196-mobile-backbone-full336/report.json)与[独立核验](../../outputs/mobile-backbone-full336-audit-2026-10-12.json)。

R144–R159树调度研究另存于 `reports/project18-tree-research.tex`（4页独立PDF，R157冻结）。纯DFS年龄DP在旧48/新36均零改善；真实原次序归因后，双unary链逐原交错将旧48的COPY10153→10149、新36的1348→1342，但预算unknown分别增到18/13。全部已合法incumbent保留，原12/7证书及输入分母不变；根代理728次原JSON重放与100局部3648种原次序枚举复核通过。这是显式研究，不改默认auto或全336质量记录。

固定一般双子树次序诊断 `experiments/r158-tree-fixed-pair-diagnostic` 的真实ragged64单提案23→21；两串行控制28/23对交错21确认机制，首次R160失败原件保留。R163新增40二元分支/外部上下文输入，独立完整8960次序枚举全部匹配。R164唯一固定84 warm-start实际COPY11491→11487，仅3图改善4COPY；65合法/19原证书不变，43预算partial、10completed、31不尝试，236实际完整候选全部保存。root独立367全block重放通过。收益不足默认替换；完整4页独立报告 `reports/project18-subtree-research.tex`（R165冻结），全336/default与历史报告不改。R166静态预算归因仅从冻结文件读取，真实unfinished frontier未保存不补造；下一固定w=2 AWA*方案 `research/level-stage/tree-pair-anytime-plan.md` 尚未实现/测试。所有成功子集均值和局部收益不作为官方Level达标。

R110–R118离线可行性研究：原17未输出输入中，9份completed/live闭合证书及6份原数据图rook minor证书在严格原身份模型证明不可行，余下两个矩阵实例仍未知。这没有增加合法输出，R109的272输出及192929 COPY保持原记录。新的原顺序桥梁以未来数据身份生存集合为状态，满窗时必须最后消费至少一个旧身份；COPY旋转可物化满足条件的顺序，寄存器顺序依赖仅限制ready而不增加临时值生存。2000个已保存物理年龄oracle对照、240个新增自由阴性对照都保存正／负／未知状态，证明文档见`research/level-stage/retention-order-proof.md`及`rook-minor-proof.md`。

可选CP-SAT环境独立于默认标准库环境，模型允许所有内部MUL/ADD交错。2240次原模型对照中2118可行输出通过身份／符号／三整数重放，122求解器INFEASIBLE与已有否定一致，没有矛盾；INFEASIBLE仅为backend结论，没有便携闭合证书。两个矩阵实例单worker各30s均UNKNOWN，不是无解。可运行以下命令；`Round`须为新目录名，输入、实际模型和结果保留哈希。默认`auto`和旧报告未改。

```powershell
.\scripts\setup-cpsat.ps1
.\.venv-cpsat\Scripts\python.exe scripts\research_cpsat_audit.py --round my-cpsat-audit --oracle-report experiments\r111-retention-oracle\report.json --input experiments\r111-retention-oracle\inputs.jsonl
.\.venv-cpsat\Scripts\python.exe scripts\research_cpsat_matrix.py --round my-cpsat-matrix --budget-ms 30000
.\.venv-cpsat\Scripts\python.exe scripts\research_cpsat_symmetry.py --round my-symmetry-holdout --holdout --budget-ms 2000
.\.venv-cpsat\Scripts\python.exe scripts\research_cpsat_symmetry.py --round my-symmetry-matrix --budget-ms 30000
```

R120/R121另试经完整raw数据图automorphism核验的行／列GET组首次出生排序，仅显式研究，不固定内部k/MUL/ADD顺序。新24图两侧同9构造、3否定、12未知；共同输出COPY63→61但2例退化，未作COPY优化。原2矩阵与实际冻结R119源30s配对均UNKNOWN（总121.500s），未新增原336输出。新的独立报告为`reports/project18-feasibility-research.tex`，旧报告保持冻结。

2026-10-11新研究检查点R109：显式`age_portfolio`保留R102已验证候选，针对严格共享归约图增加物理年龄搜索和角色状态缓存；默认`auto`仍保持旧v14。原336两侧均272合法、47限定模型证明、9预算失败、8启发失败，共同272图COPY194519→192929，其中1236归因于新年龄候选，另354为旧候选在有限预算中的完成差异。新72真实拓扑持出均62合法、9预算失败、1启发失败，COPY21752→15538；成功子集9.3227%不代表全72平均或官方Level1。153回归通过，10000双侧9998合法、2证明，COPY均562。证据见`experiments/r109-age-validation/source-provenance.json`，独立新报告为`reports/project18-age-research.tex`；以前报告与快照保持冻结。

官网更新读取日期：2026-10-10。当前版本0.3.0加入增量调度、合法原序快速路径、有界搜索改进和成批研究对照，可以直接接入已知格式的数据。

最终研究里程碑为 `experiments/milestone-v14`：133回归全部通过（49.249秒），10000固定种子小图9998合法输出、2个限定原身份模型容量证明（7.618秒）。336大图旧基线/当前分别174/269合法输出；当前另47模型容量证明、12预算耗尽、8启发失败，零错误输出。共同174图COPY20324→15213，40改善、132相同、2退化，新增95输出。269份严格序列化输出重新读取后均通过独立符号、三整数配置和原节点整数身份重放。旧基线无排列见证，只宣称符号/数值验证，不补称身份通过。完整证据、源码清单、测试执行与复制来源见 `validation-provenance.json`；v13旧基线评测适配错误原件保留，统计不可使用。

默认新增窄结构优化：仅W=4、hazard、完整不相交双GET根组、ADD/MULW每个仅一个专用SET、唯一不相交读写寄存器，采用线性尾部三计算发射；实际COPY达到独立原JSON下界后，经过原身份检查才零容差最优停止。R80/R81的匹配子集8/4图中位加速10.277/9.480倍；整批32/64图中位仅1.058/1.002，不能推广子集收益。其他结构保留原组合及回退；显式bound_portfolio的0.5%余量不用于默认auto。

## 已具备的能力

- 将 `t#d` 相对引用解析成 DAG；支持 `GET`、`SET`、`ADD`、`MULW`、`COPY`。
- `stable`、`ready`保留旧基线；`stable_fast`、`ready_fast`用增量结构严格复现选择结果，`pressure`、`demand`、`incremental`提供需求/压力启发式，`affinity`处理多输出共享机会，`size_pressure`在严格筛选森林中优先较大同需求子树。`deadline`与`age_first`仅保留显式研究选项，未进入auto。`auto`保留经独立验证的最好候选，原序合法时直接达到零新增COPY下界，否则组合增量策略与有界搜索。
- 自动插入合法 COPY 接力，重映射全部相对引用；距离最大允许 `2 ** bit_width`。
- 独立结构校验和符号等价校验；GET/SET默认只保留同寄存器RAW/WAR/WAW依赖，不同寄存器访问可互换，验证器逐寄存器比较访问轨迹。
- 输出 COPY 数量、两种分母的占比、调度耗时；CLI、样例、批量基准及测试已接通。
- 支持目录/单个JSON/JSONL批量输入，生成CSV及JSON报告，包含正确率、失败分类、两个COPY分母、时延分位数、种子和输入哈希。
- 调度失败或非法输入退出码`2`；搜索预算耗尽且无已验证候选退出码`3`；批量报告出现错误输出退出码`4`。启发式失败不等于数学上无解。

## 一键运行全部自建测试

```powershell
cd F:\Hackathon\projects\18-isa-scheduler
.\scripts\evaluate.ps1 -Count 10000 -Seed 18
```

该命令顺序执行环境检查、回归、样例benchmark、10000个固定种子小图差分及寄存器排序审计。测试数量随研究增加，以运行输出为准。历史v0.2、hazard模式、100ms预算的实际结果：stable/ready/auto分别成功输出9930/9992/9998个；**所有输出独立校验通过**。余下2个只在保持原DAG边、单次执行、COPY接力、不重算或合并等价值的搜索模型中证实无解，不能据此宣称原题无解。

历史自建小图包含wide、branch、highfanout、GET/SET hazard四类，每类在2…5 bit各625个用例。v0.2 auto救回5个两种基线都失败的图，在503个图减少COPY；这些是本地研究指标，不是官方成绩。

证据：`outputs/fuzz-10000.json/.csv`、`outputs/benchmark.json/.csv`、`outputs/register-order-audit.json/.csv`、`outputs/counterexamples/`。各成功结果除独立符号校验外，还执行任意精度整数、signed8、unsigned16三个明确配置的数值差分。

排序审计发现：早期conservative模式强制所有GET/SET保持顺序，产生11个模型内无解，其中9个在只保留同寄存器hazard后得到合法方案。这是实现约束造成的失败，现已修正默认模式。可通过`--memory-order conservative`保留早期模式作对照，不能将其无解结论冒充题面结论。

## 环境与运行

已建立本目录 `.venv`，验证版本为 CPython 3.12.14 / Windows x64。运行和测试均只依赖标准库，无需 GPU、LLVM 或第三方包；从项目根目录运行模块，不要求安装发行包。

```powershell
cd F:\Hackathon\projects\18-isa-scheduler
# 首次在其他机器运行时，使用 Python 3.11+
.\scripts\setup.ps1 -PythonExe python
.\scripts\test.ps1
.\.venv\Scripts\python.exe -m isa_scheduler optimize fixtures\far-dependency.json --strategy stable --output outputs\far-dependency.optimized.json
.\.venv\Scripts\python.exe -m isa_scheduler verify fixtures\far-dependency.json outputs\far-dependency.optimized.json
.\.venv\Scripts\python.exe -m isa_scheduler benchmark --output outputs\benchmark.json
.\.venv\Scripts\python.exe -m isa_scheduler batch fixtures --output outputs\batch-report.json
.\.venv\Scripts\python.exe -m isa_scheduler batch path\to\inputs.jsonl --strategies ready,auto --output outputs\jsonl-report.json
.\.venv\Scripts\python.exe -m isa_scheduler optimize fixtures\official-known-input.json --strategy auto --strict --output outputs\submission.json
```

若 PowerShell 限制脚本执行，可直接使用上述 `.venv\Scripts\python.exe` 命令，无需修改系统执行策略。需要重建环境时可显式传入本机 Python 绝对路径：

```powershell
.\scripts\setup.ps1 -PythonExe "C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
```

## 输入、输出与边界

输入为一个 basic block JSON，字段 `block_id`、`bit_width`、`instructions`；每个相对引用表示当前指令前 `d` 条指令的输出。输出核心字段为 `block_id` 和 `optimized_instructions`，本地额外提供 `stats`。若官方提交器要求严格字段白名单，接入时移除 `stats`。

`official-known-input.json`转录官网已知三条指令输入示意；其block_id由本地命名。其他`fixtures/`是构造的验收样例，其中`infeasible-window.json`在2 bit下用于确认有界失败，3 bit下可以运行。`large-highfanout.json`实际覆盖大于10节点的beam路径。它们都不是官方评测集。当前不宣称达成官方≤10%或≤2%的平均COPY目标。

数值解释器由`IntegerSemantics(word_bits=None/1…128, signed=False/True, overflow="wrap"/"error")`显式配置：ADD和MULW采用该整数模型，MULW截取低word_bits位的设定仅为本地研究假设。任意精度模型默认设4096位安全上限，超限会跳过该数值配置并在报告写明，仍运行固定宽度检查；本次10000小图未触发跳过。官方算术位宽和溢出规则仍需确认。符号校验保留运算符和有序操作数，不采用代数改写；它不依赖猜测溢出语义。签名使用SHA-256，属于工程校验，不是形式化证明系统。

## 搜索证明和预算边界

小图oracle默认最多10条原始指令，在有限状态空间按新增COPY数量做一致代价搜索；状态保存已完成节点和活跃值距当前指令的年龄。它允许提前COPY，不局限于到期接力。队列完整耗尽或弹出最优终点时才报告`optimal_under_model`/`proven_infeasible_under_model`。证明范围是保持原DAG边、每个原节点只执行一次、按所选memory_order处理寄存器依赖、仅新增COPY、不重新计算或合并等价值。默认hazard只限制同寄存器RAW/WAR/WAW；conservative额外强制全部GET/SET顺序。两种模式的模型内证明都不能外推为原题无解。

`auto`对大于10节点的图使用beam，裁剪后始终不声称全局最优。默认预算100ms、30000扩展状态；已有候选时的大图搜索额外预算限制在5–25ms。零新增COPY达到该目标的非负下界，可以结束搜索。统一代价搜索以COPY成本为第一优先级，同成本优先完成更多节点；年龄支配是可选精确模式研究开关，实测比较开销较高，默认关闭。预算检查发生在工作单元之间，解析、校验和文件I/O另计，因此不是操作系统级硬实时保证。预算用尽时保留已校验候选；没有候选才报预算耗尽。使用`--time-budget-ms`和`--max-states`调节。30ms历史压力运行曾出现一次预算耗尽，已单独保存`outputs/budget-30ms-observation.json`，没有把它解释成无解。

## 可复验的研究对照

```powershell
# 新目录保存证据，避免覆盖历史结果：当前回归、10000小图、21拓扑大图旧新对照
.\scripts\research.ps1
# 按最终里程碑的336图规模运行（默认Samples=2为672图）
.\scripts\research.ps1 -Samples 1 -Round my-final-replay
# 仅重放同一384输入的旧新对照
.\.venv\Scripts\python.exe scripts\research_benchmark.py --round my-new-round --input experiments\r1\inputs.jsonl --variants v02_auto,current_auto
.\.venv\Scripts\python.exe scripts\research_analysis.py experiments\my-new-round\report.json
# 精确搜索消融、独立进程内存观测（tracemalloc使该脚本的时间不能当作吞吐成绩）
.\.venv\Scripts\python.exe scripts\research_oracle.py
.\.venv\Scripts\python.exe scripts\research_resources.py
# 重新读取已保存的严格输出并独立验证，不调用调度器
.\.venv\Scripts\python.exe scripts\replay_outputs.py experiments\r10-prepared
# 最终269保存输出：独立三整数重放，以及无哈希依赖的原编号身份补充证明
.\.venv\Scripts\python.exe scripts\replay_outputs.py experiments\milestone-v14
.\.venv\Scripts\python.exe scripts\research_identity_replay.py experiments\milestone-v14
# 固定顺序精确接力审计（仅研究；非所有重排的最优证明）
.\.venv\Scripts\python.exe scripts\research_fixed_order.py --source experiments\r11-traces --round my-order-audit
```

阶段r3在384个32/128/512/2048目标节点、8拓扑×4窗口的输入上：v0.2/新版分别验证通过278/304个；共同成功278图COPY18035→16580，20改善/258持平/零退化，救回26个，中位逐输入加速3.05倍。另256个新种子、64/256/1024/4096规模留出：139/199通过，共同139图无退化，救回60个，中位加速3.60倍。所有输入哈希、失败/预算类别、独立验证成本和逐条结果都保存在`experiments/r1,r2,r3,holdout/`，历史负面结果也保留：r1因为去掉大图原序基线导致30图COPY退化，已修复。成批结果不能证明官方平均COPY目标；成功集合变化时必须比较共同成功子集，并单列失败。

独立中文单文件研究报告为`reports/project18-research.tex`，包含一手相关文献、算法模型、硬件、成本和限制；持续研究时随批次更新。CPU Ryzen9 8945HX，31.3GiB内存，当前单进程；未测目标ISA执行周期或功耗。

完整里程碑`experiments/milestone-v03`已实跑10000小图9998成功及192个十二拓扑大图：v0.2/新实现110/161通过，共同110图COPY减少20.4%，22改善/87持平/1例多一条COPY，新增51可行输出。静态图复用批次`r10-prepared`保持161输出和全部COPY不变，p50 45.21→38.63ms、p99 277.29→257.43ms；161份严格序列化输出重新读取独立验证全部通过。固定顺序审计161份中120份已达下界，12份小窗口搜索只1例改善一条COPY，故没有加入默认优化器。已测峰值与规划硬件、单开发者工作日估算见研究报告。

后续`milestone-v04`已一键运行10000小图和224个十四拓扑大图；共同122图COPY减少39.3%，但仍有1例多一条COPY，不是官方成绩。当前生成器十八家族，新增随机不平衡/带填充树、点积/stencil/矩阵模板和全部数据到达SET的稀疏图；三个计算模板种子只改标识，不能当作独立结构留出。树工作量顺序带来质量收益；`forest_work`、`branch_dp`、`branch_portfolio`仅作为显式实验选项，已保存无效和退化结果。严格容量证书及离线闭包/前缀枚举只约束原值身份保留、原计算单次执行、COPY-only模型；原25个失败的离线解释不能替代在线成本/预算记录，也不能冒称官方题目全局无解。

独立验证器目前一次扫描原始JSON完成格式、引用与符号检查，不读取调度DAG。91份序列化输出交替旧新各三次验证，中位1.83倍加速；整体优化同图中位只有1.07倍，COPY和可行数不变。最新完整数据、负面实验、工作日/硬件估算见`reports/project18-research.tex`和`experiments/r15-*`至`r30-*`。可独立执行失败容量审计：

```powershell
.\.venv\Scripts\python.exe scripts\research_branch_capacity.py --round my-capacity-audit
.\.venv\Scripts\python.exe -m isa_scheduler optimize fixtures\official-known-input.json --strategy branch_portfolio --strict
```

第二条用于接口试运行，三指令官网示例原序合法，会直接输出零COPY；分支策略收益需用多输出共享图评测。

当前生成器已扩至21家族：新增近窗口长脊柱、串行链及有序重复算术网络。默认对严格完整纯单源链直接发射零COPY，原节点全部保留；新32图512–16384节点持出全部正确，旧版30图正确，逐输入中位约2.06倍加速。一般`forest_portfolio`、`alias_pressure`仍为显式实验；前者扩大规模出现预算退化，后者虽然救回6个身份模型证书输入，但共同成功35图21处COPY退化，不能当作默认收益。别名只复用相同有序纯算术或原COPY，GET/SET各自独立，不删除或新增原指令；官方是否允许操作数等值替换未明确。显式新模型完全绕过身份容量证书及固定顺序COPY下界。

`milestone-v10`实际106回归（43.41s）、10000小图（10.58s）、336大图（97.54s）已完成；小图9998正确输出和2身份模型证书。大图旧新183/272输出，共同183图COPY 21575→16219，41改善/139不变/3退化；89救回，47模型证书、9预算、8启发失败。272份严格JSON输出重新读取、不同初值与3整数模型独立重放全部通过（5.68s）。不同里程碑的CPU竞争会影响有限预算可行数，历史负面结果保留。近窗口8192节点产生超过12万COPY，原峰值工作集315.44MiB、参考字符串复用后同图约265MiB；这是已测案例，不是所有搜索的资源上界。无GPU依赖。

在线20/27节点纯闭合子图容量证明有10/15ms独立上限，只有DP完整穷尽才拒绝输入；超预算为未知，不会宣称原题全局无解。一般矩阵/点积的宽窗口预算失败仍保留。`local_swap`为新的显式实验：保留已验证自动候选，在至多512节点、128试探、50ms内尝试相邻合法交换，只有COPY严格下降且独立验证后才晋升；尚不替代默认。语义/字段严格验证提速与优化质量分别计量，全部证据见研究报告。

最新`milestone-v11`118回归（38.51s）、10000小图（8.86s）、336大图（97.40s）：新272正确、47身份证书、9预算、8启发失败；共同182图COPY21601→16231，42改善137同3退化。272严格输出另换初值独立重放全通过（6.87s）。后续`local_relocate`、`minor_portfolio`、`branch_copy`均为显式成本/质量实验；局部重排和整分支beam改善不到1%而延迟显著增加，minor预检可能损失预算案例，均不默认。

新`bound_portfolio`也显式：针对至少512节点的严格纯图，以所有重排适用的身份模型COPY下界，在已验证候选剩余可降低COPY比例≤0.5%时提前停止。强制脊柱使用持久根年龄和下界，通用纯图另用每个值的不同原consumer数量下界，两者取强者；独立原JSON证明检查后才停止。它不宣称精确最优；R67新64图至16384节点全部正确，COPY+0.121%，逐输入中位加速2.51×。R73另新48图含不匹配树与在线独立证明成本，40正确/8身份证书，COPY+0.086%，整体中位1.19×、匹配脊柱1.87×。R74隔离跟踪16384节点/24万COPY样例，普通/显式工作集约510/245MiB，COPY+0.139%；跟踪墙时不是普通吞吐。近窗口至少2048节点的新32图中，当前结果距离全重排必要下界最多0.60%；巨大接力数不能仅靠身份重排达到2%占比。该结论只限合成输入、本地运算和原值单次/COPY模型，不能推广官方评测或允许别名的重写。

```powershell
.\.venv\Scripts\python.exe -m isa_scheduler optimize fixtures\official-known-input.json --strategy bound_portfolio --strict
.\.venv\Scripts\python.exe -m isa_scheduler optimize my-large-spine.json --strategy bound_portfolio --copy-gap-tolerance 0.001 --time-budget-ms 4000 --strict
.\.venv\Scripts\python.exe scripts\research_spine_margin.py --round my-spine-margin
.\.venv\Scripts\python.exe scripts\research_minor_audit.py --source experiments\milestone-v11 --round my-minor-audit
```

`--copy-gap-tolerance`是当前COPY中至多还可减少的比例（默认0.005，即0.5%），不是COPY/输出占比，也不是官方2%门槛；仅显式`bound_portfolio`使用。0要求精确达到下界，其余不匹配图继续普通组合。所有阳性证书可用原始JSON独立重建链/根区间或不同consumer集合；新增通用下界与240个小图完整年龄状态oracle交叉核实，重复操作数只算一个consumer。证书不适用于别名、重算、额外GET、spill或原节点可删除模型。

```powershell
.\.venv\Scripts\python.exe -m isa_scheduler optimize fixtures\official-known-input.json --strategy alias_pressure --strict
.\.venv\Scripts\python.exe scripts\research_benchmark.py --round my-alias-round --families ordered_duplicate_network,butterfly,sparse_shared --sizes 64,256,1024 --samples 2 --seed 2500001 --variants current_auto,alias_pressure --before current_auto --after alias_pressure --time-budget-ms 500
```

## 目录

| 路径 | 职责 |
|---|---|
| `isa_scheduler/model.py` | 输入解析、DAG及寄存器顺序约束 |
| `isa_scheduler/scheduler.py` | 稳定基线、ready-list策略、COPY窗口治理 |
| `isa_scheduler/incremental.py` | 增量活跃值、就绪堆、需求优先级及严格基线复现 |
| `isa_scheduler/search.py` | 小图精确oracle、有界beam |
| `isa_scheduler/bounds.py` | 严格筛选的森林容量证书、固定顺序COPY下界 |
| `isa_scheduler/fixed_order.py` | 固定原指令顺序的精确接力研究oracle |
| `isa_scheduler/optimizer.py` | 已验证候选保留、策略组合和搜索回退 |
| `isa_scheduler/verify.py` | 独立结构/符号校验、整数解释器 |
| `isa_scheduler/evaluation.py` | 批量加载、分阶段计时、CSV/JSON统计 |
| `isa_scheduler/fuzz.py` | 固定种子生成器、差分与反例最小化 |
| `isa_scheduler/__main__.py` | optimize / verify / benchmark / batch / fuzz CLI |
| `fixtures/` | 基础、远依赖、寄存器副作用、窗口容量样例 |
| `tests/test_scheduler.py` | 边界与差分验证 |
| `docs/requirements.md` | 官网新增要求、实现假设及待确认事项 |
| `docs/development-plan.md` | 阶段、验收标准、人员与资源 |
| `docs/validation.md` | 本次实际验证记录 |

未知opcode/未知JSON字段默认拒绝；当前已知格式可以直接测试，不等待官方包。旧基线保留二次扫描用于研究对照，auto使用增量实现；大图仍可能预算耗尽，当前数据分布不代表真实应用或官方评测。

## Level目标的新研究阶段（2026-10-11）

官网正文重新核实仍只列Level 0/1/3，Level 2和COPY分母未定义。CC2023的代码生成完备性依赖spill，不能据此宣称本题COPY-only图皆可行。旧v14源代码、25页报告及原始结果保持冻结，新报告在`reports/project18-level-research.tex`，一手论文与正文审计在`research/level-stage/source-review.md`。

新增显式策略：`reverse_pressure/reverse_cluster/reverse_span`逆向压力启发式，`root_spines`严格共享根链，`root_portfolio`保留旧回退，`tree_portfolio`先保留旧森林候选再尝试逆向，`comb_forest`严格梳状森林零COPY发射，`research_portfolio`组合这些限定候选。默认`auto`继续采用v14算法。所有候选保留原节点、有序参数与寄存器hazard，不新增GET、不重算、不删除、不等值改边；不匹配形态的直接结构策略会失败，组合策略继续旧回退。

逆向压力在全336图有明显退化，不默认。严格共享根新60图全部合法，共同52图COPY33927→18650，救回8预算失败；但其完整60图必要COPY/输出下界10.772%，当前11.052%，在本地身份模型下连10%亦不能达到。新长填充树的逆向候选合计减少18% COPY，单策略仍有6退化，组合保留旧候选。梳状森林把唯一消费GET紧贴使用、每个算术至多一个算术前驱，所有引用≤2：新48图128–32768节点四窗口全部零COPY合法，旧版本29合法/19预算失败。完整接口有独立验证尾部，候选的250ms预算不是端到端硬墙时限。

一键执行当前完整回归、固定种子10000小图（冻结v14对照、符号/原JSON身份/三整数检查）、保留原336全量评测、两个独立磁盘重放和官方已知输入严格导出：

```powershell
.\scripts\level-stage.ps1 -Round my-level-stage
.\.venv\Scripts\python.exe -m isa_scheduler optimize my-block.json --strategy research_portfolio --time-budget-ms 250 --strict
```

每次使用新的`Round`，已有证据目录会拒绝覆盖。失败输入不移出分母；10000小图的模型失败另保存依赖闭合子图范围内的最小反例。必要下界审计可以独立执行：

```powershell
.\.venv\Scripts\python.exe scripts\research_level_reachability.py --source experiments\milestone-v14 --round my-level-floor
```

初始原336下界为6.690%（输出分母）；后续R99将全DAG强制核心和共享归约年龄和证书加入，保留同一336输入后必要下界为11.7792%（输出）/43.6376%（原指令）；既有272合法输入的必要均值为10.0864%/35.2674%。这些限定原身份单次、COPY-only、明确纯结构；不推广到别名/重算或未知官方数据分布。没有官方Level通过声明。

新增显式 `root_phases/phase_portfolio` 延迟跨链共享GET出生，保持所有原节点和有序引用。R100原336双方同272合法/47模型证书/9预算/8启发失败；8改善264同，COPY194251→194178。新64图R101双方同60合法/3证书/1预算，21改善39同，COPY75048→74780。跨组中位成本增加约17–22%，所以默认`auto`不变。`consumer_cluster/consumer_portfolio`在新持出有可行性退化，仅保留失败研究；`reduction_columns/reduction_portfolio`是严格共享点积列布局，W16/32零COPY但W8未取得相对已有pressure的质量收益。

```powershell
.\scripts\level-stage.ps1 -Round my-phase-audit -Strategy phase_portfolio -Baseline level_r91
.\.venv\Scripts\python.exe -m isa_scheduler optimize my-block.json --strategy phase_portfolio --time-budget-ms 250 --strict
.\.venv\Scripts\python.exe scripts\research_level_reachability.py --source experiments\milestone-level-r91-336 --round my-complete-floor --include-dag --include-core --include-reduction
```

三份证明在 `research/level-stage/*-proof.md`；独立raw年龄状态oracle的1200图审计和192专门正图分别为R94/R97，所有预算未知保留，未用输出对照代替必要性证明。

