# R56 阴性结果之后的有界观察设计（只读设计，未实施/编译/执行）

当前只有两组完整输出、逻辑总work、evaluations、顶层exhausted、whole error与成功plan。原12例0恢复，不能由某例work增加就断言其pair被选中、guard被调用或具体失败位置。保持原3a4f候选/R51默认/全部既有冻结文件不变。本设计供root审查，不是执行授权。

## 唯一目的与原约束

在另存的observer-solution.cpp中插入仅观察语句；逐插入块用明确marker可完全删除，删除后byte-for-byte回到冻结3a4f184源。原detector/caller/guard comparator、节点顺序、费用量、调用次数、分支、2Mcut/16Mshared、128closure、top24/种子不改；不提供新pair策略，不推测多pair有效，不调用剩余63。任何观察分配/IO不得修改或引用算法决策状态。独立baseline仍使用刚执行的79cecEXE保存12输出；不能重跑baseline或从候选输出制作期望。

候选执行如获另行授权，另建G所有目录和process TEMP，fresh RAM/G1GiB/F64MiB、首失败保留。本阶段无source materialization、compiler、solver、reference batch、TeX或默认变更。

## 原源阶段标签与直接证据

1. `projection-wrapper`：记录cut.work/evaluations/exhausted/order长度，记录转入r48的remaining；记录r48.work/exhausted及最终total。原包装器返回的是r48的exhausted，未合并cut.exhausted，因此当前两个work恰为2M且顶层exhausted=false的例子不能解释成“内部从未耗尽”。观察必须显式分别记录两层。
2. `original-cut-no-fit`：唯一原`single<0` dispatch点，记录实际prefix、done/degree/users/live、held top24及当时work/limit。此状态只在执行真正到达该点时记录，不能据旧R52插桩状态冒称R56状态。
3. `restart-entry`：entry charge前后work与实际paid结果。`detector-return`记录complete/exhausted、原ID producer/target（无pair为null）、workbefore/after。读取观察字段不替代源码原有status/dispatch收费。
4. `caller-status/dispatch/merge`：每次费用是否支付与work before/after。在merge未付时记录retry内部order长度，但保留原caller清空结果语义；原partial helper不得视为whole成功。
5. `guarded-whole-exit`：从原空状态的一次guard，在所有真实return点记录stage枚举、work/limit、prefix长度、delayed/target原ID、target是否实际完成、original users/degree/live。区分paid no-ready-fit、probe exhausted、apply budget、scan budget、held sort budget、complete等，不据费用数猜测。
6. `guarded-probe`：累计真实calls/valid/exhausted/cap128/no-ready-fit；仅前述真实分支累加，不添加原未执行的reachability或搜索。必要第一失败snapshot记录C原pending/order、外部DIRECT users，仍以原全图边重放。应把所有早退点编号列表冻结，不能默默遗漏一类后声称全面归因。

## 观察成本与覆盖边界

每case重置两个scope：独立helper与whole API。每scope最多保存16条阶段元数据、2份完整物理状态；每状态各数组长度<=4096（原n上界），保存prefix/done/users/degree/original pending/held及原ID映射，最多6*n整数+原n标志。超过上限仅增加固定uint64 dropped计数，第一事件/最后返回概要和各stage累计数固定字段保留。uint64计数溢出须显式报观察错误，不回写算法费用。字符串枚举固定，不从case name挑选状态。

观察不收费、费用不能凭观察变动；明确不作CPU/墙时成本比较。有限样本可能遗漏中间实际事件，报告必须保留dropped，不能以未保存事件证明没执行。root如需更宽采集，先另审而非自动增上限。

## 预声明验证顺序（未授权执行）

先源roundtrip检查每marker唯一/删除后SHA=3a4f184；审所有原return分支观察标签及收费前后插入位置。编译单独观察驱动时默认源/原EXE不得覆盖。随后如获授权，仅一次同原12执行，逐字段核helper order/plan/T/peak/work/evaluations/exhausted与whole returned/error/plan/所有非时间metrics和既有R56输出完全相同；任一不同即观察不合格，不用新数据解释改进。保存实际raw/失败/源码/所有编译输入/EXE/费用不变证据；whole与helper成功计划仍需原图独立heap重放。

只有等价性通过的真实阶段记录才可回答“pair是否完整选出、guard是否调用、在哪个原stage退出、实际哪条DIRECT用户持出导致no-fit”。旧R52的两必要界仍是不同源码路径的结构证据，不等于本候选选择/重启成功证据。
