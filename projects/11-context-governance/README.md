# 11：DevEco Code Agent上下文治理优化

2026-10-12 第二轮：已在3B NF4上完成两批真实完整/压缩测试，新增`public_prompt.py`明确草稿assistant与修复user边界，并保存第二批原提示。两批各两道既有DEV题、每模式最多两候选，共16次生成，公开选择0；全部生成结束后独立评分也0通过，不与历史30题不同配置混算。完整单元测试54项：53通过、1跳过。旧Qwen3仅加载partial仍保留，不计质量。见[本轮结果与限制](../../docs/four-project-development-round2-2026-10-12.md)和[证据清单](../../outputs/four-project-development-round2-2026-10-12.json)；下文烟测正在执行等表述为历史记录。

2026-10-12 用户要求恢复四题开发。本轮新增 `src/context_governance/candidate_gate.py`，把真实公开测试反馈接入有界候选修复，校验公开契约/spec SHA，拒绝截断思考和非布尔验证结果，并分列生成与验证时间。4项新测试通过，含真实失败→修复执行和30契约哈希核对；这是可选功能集成，不是新LLM质量收益。旧Qwen3烟测仅留下加载完成的partial，未完成结果不计正确率。历史文件保留。

已接通固定工程快照、完整Python AST、跨文件依赖保护、精确Token预算、真实模型与可信功能评测。治理核心仅依赖标准库，模型使用独立 `.venv-model`。数据与oracle自行构造，不代表官方隐藏测试。

当前进入正确性优先的新阶段，用户已授权继续，旧35%停止门槛不再适用。先完成主论文研究，再检查压缩语义保护与生成程序需求正确两层；通用公开契约候选/修复机制隔离在 `adapters/correctness-v26`，修正契约在 `adapters/correctness-v27`。全30题公开契约兼容审计通过，旧v22模型仍20/30；公开测试通过不是全域证明。官方Qwen3-8B已下载并逐文件验证，固定两题GPU烟测正在执行。详见[新阶段研究和计划](docs/correctness-v26-research.md)。

上一阶段默认single/resident/literal-v17。v22固定30题完整19/30、压缩20/30，未增加压缩正确数；v24真实GPU API兼容验收48短+1长完整greedy ID通过，25模块已按冻结包提升src。核心48/48无跳过，测试运行157.667秒、完整流程墙时161.1432915秒，二者口径分开。北京时间2026-10-11 06:30旧额度条件曾触发停止；该历史结果与研究报告继续冻结保留。

```powershell
.\scripts\verify.ps1
# 默认小模型6题，写新结果，保留历史证据
.\scripts\test-model.ps1 -Repeats 3
# 20题多文件修复，3B分块预填充；复核不读取隐藏测试
.\scripts\test-model.ps1 -Model models/Qwen2.5-Coder-3B-Instruct -Suite fixtures/engineering-v5 -Repeats 2 -SelfReview -PreparedContext -Output artifacts/my-3b-review.json
# 新机需已有兼容CUDA PyTorch
.\scripts\setup-model.ps1 -Python C:\path\to\python.exe
# 可选NF4环境及约15.2GB公开权重下载
.\scripts\setup-model.ps1 -ModelRepo Qwen/Qwen2.5-Coder-7B-Instruct -ModelDirectory models/Qwen2.5-Coder-7B-Instruct -Quantization
```

7B NF4单调用在原20题上完整17/20、压缩18/20，无成对退化；80次生成墙时594.32秒，累计输入Token加权减少89.09%，端到端TTFT逐题均值改善85.45%。首次测量前固定的新增6题完整1/6、压缩2/6，24次生成墙时425.57秒，暴露复杂验证、排序与重复项的错误。两组不能合并宣称通用质量达标；首次测量之后这6题也成为开发数据。证据为 `artifacts/research-model-v8-nf4-7b.json`、`research-model-v9-holdout-nf4-7b.json`，40+12提示hash及80+24功能结果均已独立重放。

3B双调用20题160次生成：完整13/20、压缩16/20，无成对或初稿到修订退化。静态AST提示没有增加正确率，保留负结果。累计输入Token加权减少87.01%，第一稿TTFT逐题改善均值87.93%，到最终代码的阶段耗时估计改善26.07%。复核有额外成本，第一Token不代表最终答案完成。证据 `artifacts/research-model-v7-contract-3b.json` 和冻结源码 `research-v7-source/`。7B与3B的比较同时改变模型及权重精度，不能归因于单一因素。

单调用14题3轮3B完整/压缩均10/14，输入Token加权减少90.89%，端到端TTFT逐题改善均值88.48%。23会话缓存工作负载选择一致，温热治理中位加速2.64倍，初始化与冷启动另计。实际131072 Token重要性分析为6分布各30次，最高p95 53.84ms；只测CPU分析，不进行128K推理。

7B NF4普通复核的26题固定开发集合完整19/26、压缩20/26，无成对或初稿到修订退化。相对单调用没有提高压缩组正确率：原20题仍18/20、结构6题仍2/6。208次生成的纯模型耗时1498.01秒、含加载/warmup/检查的完整管线2017.64秒；输入Token加权减少85.66%，第一稿端到端TTFT逐题改善85.22%，到最终解码改善38.05%。52个初稿和104个复核提示hash、208个功能结果及模型文件已独立重放；因此额外复核保留为可选成本，不能宣称它有质量收益。

7B NF4三阶段批评在相同26题上完整21/26、压缩20/26；归一化和稳定拓扑两题由完整正确变为压缩错误，质量门槛失败，不进入默认。312次生成墙时3938.74秒，累计输入Token减少83.27%，第一稿端到端TTFT改善83.32%，最终完整解码改善32.84%。52个初稿、104个批评、104个修订提示hash及208个功能结果按起始检查器SHA独立重放。证据 `artifacts/research-model-v12-critique-nf4-7b.json`。

可选TypeScript编译器基座：先运行 `scripts/setup-typescript.ps1`，使用 `TypeScriptContext` 常驻Node worker返回完整源码块和保守依赖。TypeScript 6.0.3锁定在 `adapters/typescript/package-lock.json`；5项适配测试包含真实tsc编译/Node执行、Unicode/CRLF、helper编辑缓存失效和ArkTS专用语法回退。8个工作负载各11轮的温热请求中位加速2.21倍。具名类型专用导入在无模块初始化的边界内按符号闭包精简；5种规模的保护Token从247/842/3394/14747/62934降为72，其中4种由超650预算变为可用。最后一项只分词、不推理。完整SDK、DevEco注入和ArkTS语义编译尚待完成，详见 [适配说明](adapters/typescript/README.md)。

新增4个工作流任务在任何模型测量前固定于 `fixtures/workflow-holdout-v13b`，16个可信方法的参考实现全部通过，占位实现全部拒绝。v13初稿测试清理错误保留在审计记录中，v13b已修复。首次7B NF4单调用16次生成完整/压缩均0/4，失败涉及完整验证、深拷贝、补丁原始坐标及缓存状态，输出158–439 Token没有耗尽512上限；347.82秒。8提示hash和16功能结果独立重放，模型文件复核。首次测试后新四题成为开发数据。26旧题+4新题仅用压缩保留模块重建后，独立参考目标全部通过，证据 `artifacts/selected-dependency-audit-v13.json`；参考实现正确不计作模型生成正确。

实验选项 `-SelfReview -CritiqueBeforeReview` 增加公开要求的模型批评；`-SelfReview -PublicExampleReview -FeedbackMaxNewTokens 768` 改为生成受限JSON字面量样例、执行被检查的初稿、再修订。两者互斥，样例预期可能错误。隐藏功能测试在每条mode/repeat流程的全部模型调用结束后独立评分，结果不进入该流程或后续独立流程的提示。4项新增测试验证注入/超限拒绝、公开函数范围、异常样例、失败反馈稳定性。质量候选结果另存，未验证改善的选项不成为默认。

本机Python3.13.12、PyTorch2.12.0.dev20260408+cu128、Transformers4.57.6，RTX5070 Laptop GPU约7.96GiB。3B FP16以1024 Token连续分块预填充运行，CUDA allocator峰值约6.18GiB，本进程RAM约9.94GiB；7B NF4实测分别约6.21GiB、5.71GiB，CUDA reserved约6.60GiB。0.5B/1.5B/7B为Apache-2.0，3B为Qwen research license；每文件commit/大小/SHA256及许可留在各模型目录。下载保留TLS验证，权重不纳入源码管理。`scripts/record-model-environment.py`记录本机29个有效依赖及版本，不是通用CUDA安装锁。

`fixtures/engineering-v5` 包含边界、非法输入、顺序/不变性、已有导出和helper实际调用。原20题中后增六题仅固定目标文件，由已有imports拉入非保护helper与配置链；另六个结构任务中三题有helper导入、三题没有。隐藏测试/oracle不进入模型快照。可信AST门槛只针对纯函数，并非通用Python安全沙箱。`PreparedContext` 由调用会话持有，内容/依赖改变拒绝复用，计数器改变清空成本，接受预算仍精确重算。

```powershell
.venv-model\Scripts\python.exe -m context_governance.verify_recorded_eval --report artifacts/research-model-v7-contract-3b.json --suite fixtures/engineering-v5
```

重放验证快照、模型、prompt hash、实际tokens与功能结果，不重新生成。历史核心48项回归47通过/1可选torch跳过、100.11秒的原记录保留；最终v24提升后的模型环境CPU回归48/48通过、无跳过，测试运行157.667秒、完整流程墙时161.1432915秒，证据[最终核心日志](artifacts/core-regression-v24.log)。增量TypeScript worker的5项编译/执行语义验收另批通过，11.26秒；26次编辑与旧worker同图同治理，8工作负载各11轮中位加速1.34倍、最小1.29倍，计时前原快照构造另计。新增模块初始化依赖修复包括累加赋值、循环绑定、写入及调用；现有26题图与修复前相同。46种Python编辑场景各11轮中，`PreparedContext.revised`与重建索引选择相同，中位加速2.44倍、最小1.62倍，旧快照初始化单列。DevEco/ArkTS、动态依赖、真实构建和并发session尚待开发。

v17公开样例反馈在固定30个开发任务上完成360次生成：完整19/30、压缩20/30，初稿18/20，没有压缩组正确数增益。原20题两组均18、结构6题完整1/压缩2、工作流4题两组均0。120流程32有效、88协议拒绝；事后参考审计仅4个有效流程全部通过、28个与本地参考/guard/精确比较不一致，结果不进入提示。前26题生成3308.38秒，相对普通复核1498.01秒约2.21倍；整批墙时4889.28秒，负成本保留。参考审计59项去重执行不是59个独立工程任务。完整初稿/公开例子/修订提示及240功能结果已离线复现，见 `artifacts/research-model-v17-public-examples-nf4-7b.json`、`public-subgroups-v17.json`、`public-examples-reference-audit-v17.json`。

长窗口独立v23容量观察完成32688输入/13输出：约54.07秒，CUDA活跃/保留峰值5.91/6.11GiB，单进程RAM峰值7.87GiB。与不回收的v20在同一模型上固定顺序比较，完整greedy IDs一致，单对生成256.88/54.24秒；仅一对，不能外推稳定加速或长工程代码质量。历史v14未完成阶段不改写。短提示卸载均更慢，常驻缓存保持默认。证据为 `artifacts/model-capacity-reclaim-v23.json` 和 `long-kv-token-compatibility-v23.json`。

v22修复公开协议的一轮30题180次生成已全部完成：完整19/30、压缩20/30，原20题18/18、结构6题1/2、工作流4题0/0，均为完整/压缩正确题数。60流程51协议有效/9拒绝；事后参考审计有效流程14全通过/37分歧，共56个去重case/response执行、151.403秒。协议解析成功不等于期望值可信，不增加压缩正确题；参考分歧不自动证明需求错误，结果不供任何生成使用。累计模型Token加权减少82.330324%、第一稿端到端TTFT逐题改善均值83.015106%、最终代码时间改善均值38.398636%。纯生成2057.8317897秒、公开执行109.922621秒、完整管线2553.7983267秒；60初稿/60公开/60复核提示hash及120功能结果离线重放完成。一轮不证明重复稳定性，证据：[完整模型结果](artifacts/research-model-v22-public-contract-nf4-7b.json)、[分组](artifacts/public-subgroups-v22.json)、[参考审计](artifacts/public-examples-reference-audit-v22.json)。

v24显式resident/offloaded/reclaimed API先完成CPU/FakeGPU生命周期11项与协议兼容10项，随后[真实GPU API验收](artifacts/kv-policy-api-compatibility-v24.json)COMPLETE：48短输入四方法完整greedy ID相同，另一次32688输入/13输出的完整ID与历史一致。完整验收308.8047秒，长调用TTFT51.908秒/生成57.045秒；该次CUDA allocated6348504064B/reserved6561988608B，进程RAM累计峰值7846350848B。仅作API兼容集成，不是新的独立加速或工程质量；25模块[提升src](artifacts/v24-promotion.json)，single/resident/literal-v17默认保持。v23固定单对的12.15GiB RAM同样是累计进程峰值，不可在两调用间比较，亦不可与独立容量7.87GiB混作改善。

分组注意力v19b微基准已测18shape/180调用，虽减少资源，7B长decode耗时约2.36倍、1024-token prefill约+18%，未推广默认，保留[负结果](artifacts/grouped-attention-v19.json)。v25两个已知DEV长工程扩展完整输入31128/31106 Token、治理255/445 Token，已完成CPU参考/占位拒绝与42项SHA准备；[provenance](fixtures/long-engineering-v25/provenance.json)记录模型调用0。额度停止条件触发后未启动模型测量，不算质量成果或新持出。

[研究TeX](reports/project11-research.tex) · [开发计划](docs/development-plan.md) · [测试就绪](docs/TEST_READINESS.md) · [官方要求](docs/requirements.md)
