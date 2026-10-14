# 第19题题面核对与测试源码分类（2026-10-14）

依据用户在本次会话提供的完整题面截图，标题为“动态算子图编译与并行调度”。原图保存于 `research/task19-requirements-2026-10-14.png`，861×5123，SHA256 `7c2fcecafb7892c9c84d1563e31aa5e71446f42a2e600abd9c6a51243b7f7d1f`。来源链接：https://www.chaspark.com/#/races/competitions/1326691788365586432 。本次公开网页只能获取前端资源，正文接口返回权限错误；本记录的正文依据是用户提供的截图，不能据此断言在线正文没有更新。

## 已确认的要求

1. 分析给定动态图算法 C 源码，生成表示算子间**符号依赖关系**的 Metadata。运行时读入 Metadata，计算输入 A 的分解，输出下三角矩阵 L。仅交付一个固定矩阵分解库不足以覆盖源码分析要求。
2. 明列输入为**朴素 Cholesky 与分块 Cholesky 源码**，以及多组不同宽度的 A。核心评测建模是“从参数化循环/访存关系生成动态依赖任务，再保持源码浮点语义进行并行 Cholesky”，主测试必须是 Cholesky。
3. A、L 为 double，矩阵宽度 3～10000。输入为 4 Byte 矩阵总数 M，逐矩阵 4 Byte 宽度 Ni，随后 Ni×Ni×8 Byte 行优先数据；输出使用相同布局。
4. 结果与真值完全一致，必须支持动态 Shape，硬编码得 0 分。当前验收采用完整文件逐字节比较，包含头部、上三角及正负零，严格程度不弱于题面；不能仅比较残差。
5. 对正确队伍，以一开始计的名次 r，Metadata 得分 `max(0,15-3*(r-1))`；性能得分 `max(0,85-5*(r-1))`；总分为两项之和。不正确队伍得 0 分。没有其他参赛队结果，不能把本地字节改善或时间改善直接换成分数。
6. 性能比较绝对执行时间，明确排除输入输出文件时间。题面没有进一步界定分析阶段、Metadata 文件读取/解析是否也被排除。当前分别保留 `compute_ms`、`metadata_read_ms`、矩阵读写时间；不把热循环 Metadata 读取改善宣称为 85 分项的分解加速。
7. 题面建议可使用 LLVM，先生成 IR，再提取结构化 IR 的算子依赖；引用 LLVM 22.0.0git 文档。这是题面给出的参考路径，没有写必须使用此版本。
8. 图5的执行设备标注 Kunpeng Multi-core Processor，但截图正文没有写必须在鲲鹏上运行、提交或测试。它只能证明图示选择了这个平台，不能据此推导硬件强制要求。背景图中的 GPU/NPU 也属于背景场景。当前可在 Windows/x86 AMD 平台继续验证截图明确的功能要求；具体评测硬件如果以后公布，再另作适配。ARM64 移植不是本轮必须完成的任务。

## 官方算法图与本地假设的边界

截图算法1的 `cholesky(double *A,double *L,int n)` 是右看式 Cholesky：对角 sqrt、下列 div、下三角 madd 累积，再从 A 减去累积结果。已逐行核对 `fixtures/official_naive_transcribed.c` 的函数主体，SHA256 `0363f60d7f848b33c4e42a2be0d15d8d8d89c87caeae6b103f6a3d2059fd3a39`。

截图没有给出 div/madd helper 的定义、L 初始状态、完整分块 C 文件或明确字节序。本地右看式假设为 div=x/y、madd=x*y+z 且不融合，调用者将 L 初始化为 +0；二进制工具采用小端。这些是可审计的本地契约，不能冒充官方补充定义。显式 FMA 的 Cholesky 另有测试。取得正式源码/提交环境后应复核这些边界。

## 主测试与兼容性测试

| 分类 | 源码 | 来源与用途 |
|---|---|---|
| 主测试 | `fixtures/official_naive_transcribed.c` | 官方图主体转录；helper 与初始化按上面的本地契约 |
| 主测试 | `fixtures/cholesky_reference.c` | 自设左看式 Cholesky，不能称为官方源 |
| 主测试 | `fixtures/cholesky_blocked.c` | 自设合法分块 Cholesky；动态 block、非整除尾块，不能称为官方分块源 |
| 主测试扩展 | helper/while/loop 改写与显式 FMA 的 Cholesky | 覆盖源码等价变体与不同浮点语义 |
| 兼容性/反硬编码控制 | 普通 copy、noop、负零写入、改变运算的程序、整数选择器 | 验证一般 VM 和拒绝边界；不计入“Cholesky 主测试数量” |

此前探索报告的 1666 个成功流包含一般 VM 控制，不能全部称作 Cholesky。本轮新增 `cholesky_metadata_pipeline` 单独统计三种真实 Cholesky；每份参考由原始 C 独立编译产生，分析器/VM/优化内核均不生成真值。八种编码均核对完整符号图、语义头和 PROGRAM。
