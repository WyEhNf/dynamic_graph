# 官网要求与实现边界

来源：[27号赛题官网](https://www.chaspark.com/#/races/competitions/1326715227709140992)。2026-10-10复核，官网更新时间2026-10-08 16:17。以下是要求整理；`include/problem.h`是根据官网定义转录，未下载主办方原始头文件。

## 输入与交付

- 函数：`SchedulePlan ScheduleCvGraph(const HardwareInfo&, const std::vector<OperatorNode>&, int64_t deadline_us)`。
- 硬件输入包括独立AIC/AIV核心数、流数、显存限制、Record和Wait耗时；算子包括ID、核心类别与需求、计算时长、workspace、output、直接输入算子ID。
- 输入ID可以不连续，输入记录可以乱序。数据依赖必须是DAG。提交 `solution/solution.cpp` 与 `solution/README.md`。
- 本地不要求真实AI Core；资源均为CPU上的整数离散事件模拟。本框架不接入CANN。

## 必须满足的模拟规则

1. 同流任务按 Wait → Compute → Record 执行。Wait列表可无序但不能在一个列表内重复；只有所有事件均ready后才启动Wait，累计耗时为事件数乘Wait时间，按事件ID升序解释。
2. Event非负，只有一个记录者，每个Record至少有一个Wait；禁止同流Event。允许为资源竞争增加跨流Event，但不能改变原始数据依赖或output释放规则。循环等待非法。
3. 先删除空流并压缩流ID；在时刻0开始，同一时刻按流ID从小到大尝试，某流资源不足不能阻止后续流尝试。零耗时Wait/Record即时完成。
4. Compute开始占用所属类别核心和 `workspace + output`；Compute结束释放workspace。一个producer的output直到其最后一个**直接后继Compute结束**才释放；sink output保留到全图计算结束。时间区间左闭右开，同刻先完成释放再开始占用。
5. Record不占用核心或显存，不能因此把output提前释放。AIC/AIV资源分别计算；事件ID稀疏也合法，不能按最大事件ID分配大数组。
6. `T = max(E_v)`，取所有计算结束时间而非最后Record结束时间。`T <= deadline_us`为第一门槛，随后优先最小化T，再最小化峰值显存。
7. 核心请求1至128且不超过对应池；计算时长1至1e9。公开说明常见事件/显存量级为1e6/1e9；本地转录接口的显存与Event字段均为非负int64，当前实现和边界控制覆盖至INT64_MAX，未人为增加量级上限。显存总和先检查剩余容量，绝不饱和后当作可容纳；时间/Wait总和超int64范围的方案明确拒绝（无法满足int64 deadline）。

## 本地验证器的保守选择

跨流每个直接前驱均要求消费者自身 `wait_before` 明确等待该前驱的Record。官网没有在本次正文中明确说明“之前已在同流等待同一Event”是否可免除后续显式Wait；因此当前生成器使用显式同步，避免依赖传递豁免。验证器可能拒绝某些组织方允许的传递优化，需要官方判题器对照后再放宽。

`wait_before`去重只针对单个列表，没有额外禁止同一stream在不同任务里等待同一Event。额外事件只影响时序，显存仍按原始 `inputs` 的直接后继完成情况释放。

## 当前实现与待确认

已实现：精确接口转录、ID映射、DAG检查、自包含精确资源/显存/事件模拟、6种拓扑优先级、stream数量与类型亲和候选、额外事件护栏、局部迁移/交换、严格deadline筛选；本地独立模拟器、批量JSON adapter/schema、自建可行图与失败复测。所有返回方案均先在solution.cpp内验证，再在批量CLI中独立复核。

尚未实现：任意有解图的完整可行性保证、最优性保证和官方时限下的大图优化。官网说明存在满足deadline的方案，不意味着任意单流或贪心方案都可行。当前ScheduleCvGraph已经把deadline纳入自身筛选；最多搜索256流，候选预算为36/96/220，无可行候选时明确异常。这个异常表示有界搜索没有找到结果，不是输入无解的证明。

待核对：组织方原始problem.h、官方文件格式、隐藏图规模与分布、评测平台编译器和运行时限/进程内存限制、输出方案对传递同步的判定细则。用户已说明没有官方包并要求自行设置测试，所以当前使用公开标记的本地JSON适配器与153案固定种子可行性见证测试，不等待上述资料。平台限制未公开，不以开发机建议替代官方要求。
