# R186：原336完整输入通用region实验——只准备，未执行

本轮仅 `research_general_region_full336.py --prepare`。根审后唯一预声明命令为 `.\.venv\Scripts\python.exe scripts\research_general_region_full336.py --run`，目标R187目录必须不存在；不自动重启，不跑原baseline/oracle/default，不碰旧文件。

输入逐字节无损gzip原R177/R107336；初始输出精确复用R178 `best_outputs.jsonl` 的272份真实输出/order/COPY，总192902。原47 modelproof/9 budget/8 scheduling_failure保持原件；21族全部保留。108零COPY保留，其余164合法非零全部进入同一通用region API，没有树/shared/hazard matcher筛选。没有initial64不造零COPY，更不借它们过滤等权mean。全336质量均值保持null；只另列272固定合法集合COPY/输出及COPY/原指令均值，并按21族全状态汇总。

## 固定核心和资源

R183 core263e3eea.../wrapper8e1cdf3a...原件不变。每input500ms、累计20k扩展/20k实际transition、region32/最多64、每region16出口。selector同初始实际COPY cursor按16步anchor排名，sameinitial不叠加gain。所有partial、状态/transition/时间/cap/资源停止分别保留。

完整proposal包络按本input实际F/N/W及UTF8 block_id/reg/orderedarity重新计算F+NW，label1KiB/OPEN2KiB由实际编码检查。prep逐input冻结package（diagnostic+两proposal+64MiB slack），不得复用单例硬上界。当前盘空间有限，全局累计最坏可能很多GiB，**不假设gzip固定压缩率**。512MiB reserve之外package不足或freeRAM<768MiB时不启动；当前已生成所有labels必须全量导出，然后未来tail标`not_executed_resource_unknown`，不得删旧数据/抽样/丢labels来称全跑。

输出所有complete以compact UTF8 JSONL、gzip level1/mtime0流式写、flush，JSON/gzip/sink包含在核心时钟；保存每个更差/同值输出。写完一个真实wholeoutput后wrapper再检查actualfree，资源halt保存该候选/best/partial。全部immutable/OPEN/unfinished也完整gzip流式，不暂停/延长search预算；导出和验证时钟分列。compressed SHA与decoded SHA及两个字节量记录，根能逐行无损独立审。预检查全272合法initial独立四验证，资源不足时未完成检查明确unknown，不说通过；正常执行预期272全部实际检查。

OSError/磁盘耗尽/验证错误保存failure.json与已写partial，不自动重启，不补DP或缩小输入。每input当前RSS及process lifetime峰值单列；观察采样max不是连续input峰值。不会关闭用户应用，CPU功能时间不能称隔离性能改善。

## 独立完整验证与增量物理标签证明

每baseline、所有真实complete、best均通过独立raw identity/每原一次/orderedargs/物理t#窗口/GET SET RAW WAR WAW，符号及两个异初值×三个8signed/16unsigned/32signed wrap本地整数。三个整数模型不是官方位宽语义。

大图全标签采用新 `general_region_incremental_replay.py`，**不导入生产graph/transition**：从原JSON重建数据及hazard，prefix真实physicalrows精确replay一次，包括首region原指令前COPY；每immutable predecessor传递真实最后W物理身份槽+whole g。action必须未发/真ready、有原有序操作数代表，按物理槽判断唯一将丢失的未来身份并COPY，SET槽None，deadGET仍占槽。保留所有真实外部suffix需求与regionconsumer bitmask，重复输入consumer按集合唯一计数。每step守恒原身份、mask、g、所有roles最新年龄、h全块未发原数量；OPEN和unfinished按真实immutable version重验。buffer未发布不伪称label。这样每label最多W槽，不重复扫描整个prefix，仍保留全部replaced/stale版本，不能用age-only镜像代替物理history证明。

当前仅冻结代码/原输入/initial/status join/资源包络。增量验证尚未实际执行；根review后才完整一次R187，失败原样保留。
