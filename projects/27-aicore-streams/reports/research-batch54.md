# R54：R53唯一筛选对全部剩余63图的零质量收益

本轮只有一次67图source-only功能运行：R51冻结的57个原困难失败、6个新持出失败，加R52四个已恢复控制。没有再编译；复用R53的`selected12-gcc.exe`（SHA `e5e580be74056c2a4d2b07036f618ac830c0337e6dc82c8c17815518f56e982e`），有效候选源码仍为`fcbb968cff47dd0b95edb576f1fcf0bd04e900eb0f37ecb28383607ca02f3a21`。算法仅严格final-live支配筛选，2M/16M、128/top24、种子、阈值和排序均未改。

## 输入和基线范围

`research/batch54/functional-plan.json` SHA `671ed9b558774f576f7ea57aeff4e8d04bee39d4490b0ea4aeb7cbd60f45fa33`先冻结36项输入/结果/源码/EXE/脚本依赖，root独立检查后授权运行。每条case的原硬件、节点、原DIRECT边、deadline逐字段与原来源一致，输入只有name/hardware/nodes/deadline/expected_feasible。name和expected_feasible只供wrapper记账，生产算法只接收题面参数；witness、生成族、既有计划、参考执行顺序均不作为算法输入。

全67的旧helper基线来自冻结R51原source-only诊断61+6。whole质量基线中7条使用实际当前default已保存的smoke结果（四控制加三个失败）；其余60条来自已验收的同8b7c源码R51完整功能结果，不能称为新执行的current default67，也不能拿其历史时间作性能对照。来源文件及record索引、每条原输入canonical SHA在`input-lineage67.json`和`baseline-saved67.json`单列。

## 实际执行与全部结果

owner session29846已消费真实exit0。67图driver实际exit0，独立比较verifier实际exit0；stdout/stderr、命令、F盘仅进程TEMP/TMP/TMPDIR及执行计划SHA均保存。driver0意味着所有返回计划通过两套C++事件模型，不意味着67图全部可行。

|口径|R51保存基线|R53候选|
|---|---:|---:|
|whole合法完整计划|4/67|4/67|
|原remaining63失败|63/63|63/63|
|四个恢复控制合法|4/4|4/4|
|helper合法完整计划|4/67|4/67|
|helper exhausted记录|35|35|
|helper逻辑work总和|636,931,404|637,093,426|
|helper逻辑work最大值|15,999,933|15,999,643|

**0 whole新恢复、0丢失、0共同合法T/peak变化**，四个控制完整whole plan逐字段完全相同。helper也没有新增成功，不能将其局部搜索行为或work变化冒充whole恢复。63个失败全部保留原始error、null plan和metrics，只表示有界启发式本次未解，不是不可行证明。

逻辑work有16条增加、11条减少、40条相同，总增162,022单位（约0.0254%）。这是收费模型，不是CPU耗时。单次共享功能driver wall为19.3620705秒，包含逐图helper诊断与whole solver调用；未做匹配的CPU/wall配对性能测量，不宣称速度变化。

## 冻结证据与结论限界

- raw完整结果：`reports/final-live-remaining67-batch54.json` SHA `3ef13aee2341819c7e1ce727d9c0cc9bf9d2599354908ea541bac7bc48de359b`。每个返回计划保存全部原op_id、stream、Wait/Record及T/peak；helper与whole分别保存。
- summary：`reports/final-live-remaining67-summary-batch54.json` SHA `0522f3cebc84ea229ff5b3d855d2b048ae081f81a21fa0c722df2a4bf22b46bd`，包含全部67条比较与失败列表。
- actual终态：`research/batch54/completion.json` SHA `46e9a584346ecd59172bc31baaf44c594adaae4e43eaa7bfe331630e10e260a3`；`execution-status.json` SHA `8531039c30dda1a3ca120202af41bd6e2f4e454d024c4fc9c6084ac6ed9e3ab9`。
- R53数值安全/计费控制及初次七例夹具资格失败、随后独立修订176控制，继续保留R53报告和small checkpoint，不被本轮覆盖。

对“R52只12例无收益不能推断其他55例”的覆盖缺口，本轮已检查真正全部63个原剩余图；这一冻结候选在该图集和四控制上未显示质量作用。该结论只适用于这些完整原输入与固定搜索预算，不是对任意DAG筛选价值的否定，也没有证明全部未知可行图已无优化空间。

本单项筛选保持隔离负结果，不推广默认、不继续full250/1099/性能批。默认仍为R51源码8b7c、实际default EXE c491；用户打开的旧TeX保持e6e735字节不变。下一算法须针对未解图的实际合法次序/资源瓶颈提出新依据，不能以扩大此筛选预算或改测试口径代替可行恢复。
