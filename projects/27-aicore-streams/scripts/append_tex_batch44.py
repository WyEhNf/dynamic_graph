"""Append only the new continuation report; never modify opened R31 TeX."""
from pathlib import Path
import hashlib
p=Path('reports/project27-research-resumed.tex');s=p.read_text(encoding='utf-8')
section=r'''
\section{R44：浅层消费者邻近关系恢复可行方案}
本批推广依据是原先未找到方案的输入恢复合法方案，CPU代价同时保留。
原202困难集合由139合法/63未解变为141合法/61未解；两条恢复是同一拓扑的不同内存参数。
72个新种子持出由68合法变为72合法，另恢复4个未见种子。
共同243个成功记录的$T$/峰值全部相同，0丢失、0模型分歧、0共同质量退化。
原1229记录现1168按预期通过，加72新输入后为1301记录1240按预期通过，
其中含1条预期不可行拒绝，不能称1240个合法可行输出；仍61条有witness未解。
数值金标与剖面控制另计，不作为新增独立拓扑恢复数。

\subsection{识别、前缀条件与准确剖面}
只读原节点与原始直接边，识别可选独立前缀、独立producer、consumer反链及可选terminal sink。
支持$n\le4096$、consumer数不超过512；原63未解初步浅层26条，实际候选识别20条。
名字、生成参数、witness及其顺序均不进入算法。
真实Compute开始同时占workspace和本节点output，结束释放workspace，
producer output保持到最后\emph{直接}consumer结束，sink保持到$T$。
新分支不消除冗余边、不借用额外Event的释放信用。

固定consumer顺序时，尚未打开的输入producer在首次消费之前执行。
组内工作区降序交换只在既有前缀存活恒定时成立。
若$W_a\ge W_b$，两producer的output都持有到本consumer，则有
\begin{align*}
 P_{ab}-L &= \max(O_a+W_a,\ O_a+O_b+W_b),\\
 P_{ba}-L &= \max(O_b+W_b,\ O_b+O_a+W_a),\\
 P_{ab}-L &\le O_a+O_b+W_a\le P_{ba}-L.
\end{align*}
不同前缀可能在组内提前释放时不成立。
实现逐前缀检查remaining direct users，前缀在组后继续存活或由全组共同消费时才重排；
否则保留输入顺序。恒存活756个枚举控制与变化存活负控制均保留。
根独立反例初始live101、两工作区20/10、分别释放1/100的前缀，
无条件W降序峰值121，反序111，说明条件不能省略。

诊断计数可能超出int64，即使另有可行排列。
标准库双\texttt{uint64\_t}精确记录profile，可准确释放与排序；
$n\le4096$使瞬时量小于$2^{76}$，逐节点累计小于$2^{88}$。
评分为超容量逐节点面积、峰值、总逐节点面积的字典序，
面积仅是结构评分，不能当物理时间积分。
实际计划仍通过R42修复的Event/资源模型后才接受。

共享producer的实际output加权形成consumer邻近种子，高fanout按度归一化。
评分pair最多100万，producer fanout超过64跳过评分，全部原始依赖仍参与profile。
局部插入延后关键consumer，或提前持有producer的最后consumer；
所有种子先统一评分，再给两个较好初态局部预算，避免第一差种子耗尽预算。
charged12M包含配对/邻近与profile节点边扫描；旧种子生成、排序及容器成本另计，
它不是全算法的严格指令或wall上限。
首次消费者前执行producer也不是一般DAG或非零workspace的全局最优定理。

\subsection{独立验证与保留的负结果}
初版首seed和统一排序初态均0恢复，保留原始负结果。
加入直接共享producer邻近seed后得到原两条恢复，随后补前缀条件与计数预算。
2590个Python任意精度profile/order/capacity金标及160个有界搜索有效性控制，
在真实候选源Clang UBSan下全通过，无运行UB诊断。
523个固定计划数值金标亦真实重跑全通过。
979历史回归无退化，另外直接读取R43/R44逐记录报告证明979结果全同；
144个最优审计、33证书及默认原10加新profile共11/11通过，CTest实际2.64秒。
默认priority金标20180真实重跑，不把旧UBSan priority执行说成本批新执行。

新72图包含不同规模、多个有输出前缀、producer工作区与输出、保留consumer输出、
多个sink、局部与非局部使用、0与大Event；独立Python构造并计算串行witness，
再打乱稀疏ID与节点记录。测试适配器验证witness，算法不接收它。
根另以独立Python heap-event模型实际重放249份合法计划，
包括8stream跨流Event、所有完成后再启动、分别AIC/AIV核池、
BEGIN的W+O、最后直接消费者END释放、sink保留及最后Record排除，$T$/峰值均精确一致。
两原恢复的最终计划为8stream $T=3581299$微秒，
早期串行诊断$T=3779533$微秒另存，不混淆两个阶段。

\subsection{同Release费用：恢复覆盖不等于加速}
隔离窗口两版均GCC15.2、CMake Release的\texttt{-O3 -DNDEBUG}，
原202与新72各三轮before/after、after/before、before/after，全体与失败保留。
整个配对批wall154.096秒，原36已有功能质量全同，不额外跑性能批。
\begin{tabularx}{\textwidth}{L{4.0cm}rrX}
\toprule
指标（秒） & R43 & R44 & 分别取两侧中位\\
\midrule
202全部线程CPU &21.250000&22.203125&增加4.49\%，不是逐pair典型值\\
202全部求解wall &21.983504&22.445947&全部成功、未解及恢复\\
61共同失败CPU &13.812500&15.359375&包含未解搜索费用\\
2恢复记录CPU &0.187500&0.218750&before失败、after成功\\
72全部线程CPU &2.312500&2.265625&不能外推原困难集\\
4持出恢复CPU &0.765625&0.812500&独立种子，before失败\\
\bottomrule
\end{tabularx}

202逐pair全CPU比1.158333、1.091912、1.021567，三轮都增加，
逐pair中位增加9.19\%；两侧中位增加4.49\%是另一口径。
全CLI分别中位22.998508到23.390441秒，最大工作集316129280到316268544字节，
包括DOM/witness/验证器，不能称显著RAM下降。
新72全CPU比0.979730、0.942308、0.965986，
逐pair中位比0.965986；对应全求解wall比1.032856、0.959247、1.001072，
并非三轮稳定wall加速。
此前O2候选与O3默认的功能对照没有用来计算速度比。
推广取舍是失败后恢复覆盖增加，以原202逐pair中位CPU增加9.19\%换取2参数记录恢复，
另有4持出种子恢复；不称整体加速。原成功方案保持。

\subsection{冻结与下一步}
实际单文件源SHA-256：\path{d88860f2da7eb9b18d0271abec308a2aa1e6f426742eeecd01d58d87fd7034a3}。
\path{research/batch44/provenance.json}分别记录实际默认和性能测量EXE，
测量执行路径\path{research/batch44/build/aicore_bench.exe}另存
\path{research/batch44/measured-release-aicore_bench.exe}；
\path{research/batch44/aicore_bench.exe}是O2功能文件，不是性能测量文件。
片段已展开到单文件；仅\texttt{problem.h}与标准库，不增加提交依赖。
准备脚本曾打印LF内存文本SHA，实际Windows文件为CRLF；消息标签已纠正，
冻结与功能报告一直采用实际文件字节SHA，编译输入与片段均有记录。

\path{reports/resource-cost-summary-batch44.json}保留逐pair费用、成功/失败/恢复分组及两种中位；
\path{reports/direct-normal-r43-batch44.json}是979直接对照。
原R43冻结回退、root pre-guard独立证据与旧R31打开报告保持。
下一步先输入-only识别未解61图是否经孤立单入单出链的\emph{候选顺序块}
形成可处理的消费者前沿，不随意声称链压缩保留全局最优或改变原边；
外部输出生存与节点workspace仍必须按原图逐节点profile和独立Event模拟验证。
官方包、隐藏成绩与平台资源时限均未公开，本地恢复不能作为全图保证。
'''
assert '\\section{R44：' not in s
s=s.replace('\\begin{thebibliography}{99}',section+'\n\\begin{thebibliography}{99}')
p.write_text(s,encoding='utf-8');print(hashlib.sha256(p.read_bytes()).hexdigest())
