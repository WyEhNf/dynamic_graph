# R184：固定80小图+hand11首次功能producer——预执行合同

当前仅 `--prepare`，不执行任何search/oracle/contract。预审后唯一运行命令：

`.\.venv\Scripts\python.exe scripts\research_general_region_isolated.py --run`

输入逐字节复制R183 80固定N5..9，不换输入；另加入已root独立核验的完整hand11，合计81。默认/旧baseline/旧oracle/全336均不调用。执行前逐源/逐输入SHA必须与R184 manifest相同，目标R185目录必须不存在，异常不自动重启。

## Initial独立构造与unknown

小图initial使用独立raw set+physical ring iterative DFS，原rank优先，20k states/500ms；只找第一份完整合法输出，无质量/最优声明。没有生产parser/graph/transition调用。原GET/SET hazard和每identity future consumer独立解析；按真实W槽的唯一即将丢失身份COPY接力，不能把SET当值。受限构造失败或预算unknown原样保留，仍运行广义raw oracle；不借oracle输出替换initial使候选假匹配，也不删除missing。hand11复用保存3COPY initial，只验证不重跑旧算法。

每份initial、oracle真实输出、所有complete及best分别独立raw identity/order/有序args/真实t#窗口/同reg RAW WAR WAW replay，符号解释，以及两个异初值种子18501/18502×三个8signed/16unsigned/32signed wrap本地整数配置。官网未授权这些运算位宽，报告不会称官方数值精度通过。没有initial与广义oracleclosed-infeasible矛盾；任何候选C<oracle证明的最小C立即fail closed。

## Solver/oracle与所有输出保存

Solver总500ms/20k expansion/20k actual transition/64region/32nodes/16每region，同initial不组合。complete sink在核心预算内实际编码、flush整份全block JSONL；所有同值/更差真实出口保留。四验证随后逐JSONL读取，时间单列，不嵌入核心search时钟。若四验证失败，整run failure.json与已写partial保留，绝不恢复预算或补跑。

广义raw oracle仅80N<=9：20k扩展/20k发现/500ms，任意early/old/dead COPY；optimal、闭合infeasible、time/state/discovery unknown分别保存。hand11 oracle明确not_applicable_N11。候选latest/deadline family可能比广义最优差，不把受限穷尽标global optimum。

## 全部immutable标签/OPEN/unfinished独立重放

每region先写实际JSONL，标签≤1KiB、OPEN/unfinished≤2KiB必须实际字节断言。独立从initial真实physical prefix（包含第一region原指令之前全部COPY）和immutable predecessor/action链恢复逐原输出；raw物理ring重建done_mask、每真实identity最新年龄、g真实行数、h全块剩余原数量，逐标签/OPEN/unfinished精确比较。未发布buffer不伪label，只保留原parent+phase/cursor/count，当前core没有宣称它们已经完成。不能用生产transition镜像检查；独立实现直接看真实W槽是否丢最后代表。每input导出后释放snapshot，所有labels包括replaced/stale仍保存。

## 资源/时钟与成本

实际disk free采样before/每complete/after；wrapper按真实F/N/W/reg/block_id JSON包络执行512MiB reserve，preflight与after-saved-complete资源halt保留initial和partial。当前input sampled working set、process lifetime OS peak分别标注（采样最大不是连续监测的input峰值）。OSError/JSONI/O异常保存failure，不自动重启，不删除已写输出。

分列initial构造、raw oracle、search含sink、sinkJSONIO、四验证、diagnostic materialization/JSONIO/raw replay、whole input与whole run。此为功能运行，不能据其墙时声称隔离加速。完整81状态、无initial、所有partial、oracleunknown和成功子集分母都保存；不宣称Level1/2/3。
