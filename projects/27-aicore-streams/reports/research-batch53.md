# R53：严格最终live支配筛选，小范围验收与零恢复结果

默认仍为R51（`solution/solution.cpp` SHA `8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b`）。R53隔离候选SHA `fcbb968cff47dd0b95edb576f1fcf0bd04e900eb0f37ecb28383607ca02f3a21`，只在现有release-cut候选中增加最终live严格支配筛选；没有观察器、其他策略、预算扩大或默认替换。旧用户打开的TeX字节未变。

## 变化及安全范围

固定真实Compute完成前缀D，完整cut闭集C包含producer的所有未完成原DIRECT用户及其未完成祖先，S=D∪C。最终存活输出精确等于S内原sink或仍有原DIRECT用户在S外的节点输出之和。这一值与闭集内部合法拓扑次序无关。生产候选用局部`live-R+A`：共享完成parent只扣一次，原外部用户、已完成sink及cut内新增sink全部保留，内存整数用双uint64宽整数精确表示。

只有本次同前缀中已有真实greedy验证合法的selected cut时才计算筛选；新F严格大于其final_live才跳过greedy。相等须继续比较峰值，较小须继续检验容量，首次候选没有incumbent时不筛选。pruned候选保持`valid=false`，不形成计划或不可行证书。外层推进前缀后不复用旧incumbent。

闭集129仍在原规则处拒绝，不能部分释放；128完整处理。现有4n状态复制和全部旧收费均保留，新增初始化、原节点/边读取、计数、比较和宽整数计算均按冻结逻辑收费。2M cut/16M总预算、top24、原排序、score、tie、种子和阈值均不改。筛选安全不保证原greedy完备，也不保证新增收费后固定预算覆盖不退化；这一轮不作全图最优或加速承诺。

## 冻结顺序与初次夹具资格失败

实现和逐操作计费在首次gold生成前冻结：`research/batch53/pre-gold-freeze.json` SHA `8506bade825941f87938fb28592ff80f3c2a59ab56ac2d5ded3da250ca7b2e94`，计费表SHA `96ab01a25241c61fe2263ab7e75fd4a087a1d995c584dccb94356f80a2f60bf4`。独立最终值采用bigint H(S)集合式，独立完整物理模型从原节点BEGIN占W+O、最后DIRECT消费者END释放以及sink保留计算；生产局部计数不作为gold。

初次session46552已实际exit0，8阶段均实际exit0、stderr为空：2个GCC构建、GCC176、Clang构建、UBSan176、347固定计划、同R52原12图、数值结果核对。其176数值控制、550原拓扑cut次序、347完整计划（311合法、36预期非法）窄结果一致。

随后资格审查发现64随机控制中7例使用了已无剩余DIRECT用户的producer，违反预声明前提。故**初次176预声明gate资格失败**，不能把此前数值一致写成完整验收。初次数据、脚本、计划、全部stdout/stderr与终态记录均保留在原路径；原`research/batch53/completion.json` SHA `477aa23a44cbd537ea9c2e3cebeadce71e4ec072728539627e193b612246d561`仅证明窄实际执行，不代表夹具资格。

父任务授权后只修正这7图的测试前缀为该原图的首root节点，图的全部原节点、边、硬件、deadline、种子、预算和控制数量均不变。没有给生产算法输入参考顺序。七例前后输入SHA及理由先冻结于`research/batch53/corrected/revision-map.json` SHA `88cb3d4b085614e616d08deed15ae150ea76243429812e63a93da984066a0e8d`；然后在独立新路径生成参考数据，并复用原GCC/UBSan EXE各实际执行一次和固定计划一次，未重编译、未重跑12图、未覆盖初次文件。

修订5阶段真实exit0，64随机控制全部满足producer∈合法D、O>0、有remaining DIRECT用户且C非空。最终完整176族控制为：8手工竞争/first/equal、24外部用户/sink、16交叉依赖/零值、24整数边界、8闭集128/129、64固定随机图、32计费边界。347请求分别经GCC和ClangUBSan核对，32预算exact/one-short边界通过；558小图原拓扑cut次序的最终值独立一致。347完整计划仍为311合法、36预期非法，均按期望通过，没有将预期非法计为合法输出。全部176控制记录包含部分重复参数与预算变体，并非176个唯一工作负载。

## 同12图：0新恢复，逻辑成本并非普遍改善

修订没有改变算法，因此复用同一候选源码已实际完成的R52同12原图source-only测试。12图仍4成功、8失败，0恢复、0丢失；所有helper完整order和whole plan逐条相同，合法计划T/peak相同。全部失败保留，未解释为图不可行。

|原输入简称|R51 helper work|R53 helper work|R51→R53 evaluations|whole结果|
|---|---:|---:|---:|---|
|retention 203451023|13,888,844|13,874,848|4,959→4,959|失败→失败|
|retention 203451018|115,612|117,531|149→149|失败→失败|
|recursive nonlocal leaves64|419,195|460,989|219→219|失败→失败|
|dense k96 ret1|15,968,139|15,968,139|758→797|失败→失败|
|dense k384 ret0|2,000,000|2,000,000|142→144|失败→失败|
|blind local k12|162,593|168,932|172→172|失败→失败|
|retention 203451016|15,996,808|15,994,830|2,092→2,091|失败→失败|
|dense k384 ret1|2,000,000|2,000,000|165→152|失败→失败|
|R48恢复 local k24|1,155,913|1,172,070|580→580|成功→成功|
|R45恢复 rootmem0|1,231,870|1,231,209|1,249→1,249|成功→成功|
|R45恢复 rootmem5|1,306,736|1,303,136|1,288→1,288|成功→成功|
|R51恢复 role-duration|471,850|483,219|364→364|成功→成功|

5例逻辑work增加、4例减少、3例不变。三个原预算困难图的evaluations分别增加39、增加2、减少13，均没有恢复可行计划。newwork使原cut预算与后续14M以上余量分配位置改变，这与“不增加预算仍不能保证同搜索覆盖”的设计限制一致。以上是确定性逻辑计数，不是线程CPU成本或实测速度。共享功能阶段的wall只留原始日志，没有隔离配对性能窗，因此性能收益未知，不能称整体或局部加速。

## 可核验入口和边界

- 修订终态：`research/batch53/corrected/completion.json` SHA `53678adb76603fe986b2fa9b37a7c5eb60bca87a97d6c0b89c653a96761c3345`。
- 修订gold：`research/batch53/corrected/gold.json` SHA `202e5803d47643dceb9a1a5e1f8543c992288f6ef76e829b103bc4440092ebd5`；fixed gold SHA `db50f300bc3b35e1c1627081664310b5f7f03117f57f90c6d2127707a63786c5`。
- 资格修复：`qualification-remediation.json`、七输入前后SHA的`revision-map.json`、脚本`correct_final_live_fixtures_batch53.py`；初次资格失败显式保留。
- 实际C++/UBSan与修订物理结果：`reports/final-live-{gcc,ubsan,fixed-ubsan}-corrected-batch53.json`；最终summary SHA `55ead765cdffe33e232de250496e55c9d05a9f289e49c36565d8f1504dc5afb0`。
- 同12原完整输入：`research/batch52/observer-selected12-input-only.json`；原R51 source-only结果`reports/observer-baseline-batch52.json`；新结果`reports/final-live-selected12-batch53.json`。
- 每次命令、actual exit、F盘仅进程TEMP/TMP/TMPDIR及共享功能wall在两个execution-status文件和所有stdout/stderr保留。无系统环境修改、无用户文件清理。

本轮没有跑remaining63、full250、1099常规/625数值全回归或性能，也没有推广默认。当前建议保留为安全性通过但小样本0恢复、无成本证据的隔离实验，先经父任务独立审核再决定是否有必要扩大范围；不会自动扩大预算或继续昂贵搜索。
