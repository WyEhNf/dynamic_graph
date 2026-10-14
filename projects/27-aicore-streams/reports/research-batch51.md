# R51：完整剩余DIRECT用户的动态释放cut

R51从冻结默认R48独立实现，未继承R49扩组或R50第三位置。对已完成且仍持有非零输出的非sink producer，收集其全部尚未完成原DIRECT消费者，以及这些用户全部尚未完成祖先；原DAG的互依赖、共享节点和外部使用者均保留。cut内部每步选择真实ready且容量可放的节点，Compute BEGIN同时计W+O，最后DIRECT消费者END才释放producer。新生成输出仍有cut外使用者时继续持有，sink一直保留至全图T。

这是有界顺序构造，不是图收缩或不可行性证明：最多128个未完成cut节点、24个当前持有producer候选，超过门槛拒绝整cut，不生成错误partialcut释放信用。已知可行图的cut失败不等于原图无解。内部拓扑顺序为单一确定性greedy，不增加种子。新阶段最多使用2M计费工作；失败后原R48投影使用原16M总额中的剩余预算，原threshold、种子和组门槛不变。cut的节点/边扫描、临时状态拷贝、排序比较、probe和实际apply均计费；16M是搜索计费单位上限，不是完整CPU周期或wall上限，原投影预处理口径保持历史定义。

102个独立Python大整数cut控制实际通过，含完整外部用户、错误partialcut、交叠成员、原边互依赖、sink不可释放、尚未完成producer、已释放producer、零输出、恰好MAX/超过MAX、128/129节点边界。每个控制另外保存全部原节点恰执行一次的完整单流计划和逐BEGIN/END：100物理可行、2预期物理非法，冻结R48 Clang UBSan固定计划驱动102/102符合独立gold。注意129边界控制是物理可行而可选cut拒绝，不能将这类拒绝称为图不可行。

隔离源SHA `8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b`。实际顺序O2构建和一次61+6诊断全部exit0：原61由3→4，三个已有恢复T/P恒等；新6仍0，新增恢复1、丢失0；最大计费工作15999933/15999877。独立回放新增140节点完整原图方案：`projection_unseen_high-fanout_dense_k14_ret1_seed20312441_role-duration`，T1430270恰好等于原deadline，显存峰2481低于原容量2483，原AIC8/AIV128/stream4/Events0完全不改。该图原投影target0，新kernel的frontier顺序构造补上实际覆盖缺口。原输入和实际plan分别冻结在`research/batch51/actual-recoveries-input-only.json`和`actual-recoveries-plans.json`，未使用witness或generation作为solver输入。

完整题面CLI功能一次实际完成：202由144→145，新48保持42；全部186共有合法记录T/P恒等，0丢失、0模型分歧。两个CLI都exit1，表示57+6个已知可行未解记录仍显式失败；wrapper实际exit0表示符合对照检查。原始记录、单独失败CPU/wall（仅功能运行成本）、source/input/EXE SHA见`reports/functional-summary-batch51.json`及两份raw JSON。这250记录候选产生187合法计划、63失败；没有删除困难记录，也没有改deadline/容量。共享功能运行时间不能与历史版作性能比较。

默认R48仍保持144/202、42/48；旧打开TeX保持原字节。完整候选gate已实际完成：GCC Release 14/14 CTest、现有523加新102完整计划的Clang UBSan、102新cut probe、495祖先profile和83/210组gold，以及979+36+72+12共1099条直接R48对照。1099条pass/valid/T/peak逐记录相同；625个固定计划与独立大整数gold一致，UBSan运行错误0。原26484和22878均已消费实际exit0，完整报告为`full-verification-batch51.json`和`full-numeric-verification-batch51.json`。验收冻结`research/batch51/acceptance-checkpoint.json` SHA为`5d302ad593c744d54f76f879f6268b4ec8eeb453c7a1f1e49f869138aecffa63`，实际Release冻结EXE SHA为`25ac71bc389e62f512d7597d40048e97b88783c21e895524cdba3311c6067742`，区别此前O2功能EXE。

首次Release构建实际3354 exit1：C盘临时目录产生ENOSPC，尚未启动测试；原始日志完整保留，不算算法失败或测试通过。父任务批准仅本次子进程TEMP/TMP/TMPDIR指向项目F盘compiler-temp后，88807实际exit0完成Release、14CTest及Clang构建。未删除用户文件、未改系统环境、未改冻结源码，环境修复及精确进程环境见`research/batch51/environment-repair.json`。

同Release成本计划随后由父任务授权唯一窗口并实际完成一次：session32966 exit0，完整driver墙时199.2576797秒，12个CLI trial / 1500条case执行记录。baseline为实际默认R48 archive54fc，候选为已验收Release25ac；202与48全部成功/失败各3轮交替，每轮均保持144→145、42→42，186共有T/P恒等。与历史未测宿主负载的批次不同，本次独立监测脚本在每个完整CLI trial起止和0.25秒间隔保存GetSystemTimes CPU原始计数和GlobalMemoryStatusEx可用物理内存；kernel计数包含idle，busy须减去idle。观察包含求解进程和用户背景，不等于求解线程CPU，不扣除背景活动；采样RAM最小值也不等于连续全窗口最低值。两侧使用同监测脚本，12份host侧文件均实际measured，32逻辑处理器覆盖完整宿主，最低采样可用RAM为6,334,910,464字节；不是空机。口径依据[GetSystemTimes官方文档](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes)及[GlobalMemoryStatusEx官方文档](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex)。

困难202全记录含所有失败的三轮线程CPU比为0.857803、0.937605、1.060692：逐配对中位比0.937605（减少6.2395%），独立两侧中位比0.939292（减少6.0708%）；第三轮增加6.0692%的负值必须保留，不称稳定普遍加速。逐配对solve墙时中位比0.953677，完整CLI两侧中位30.6745→28.7422秒，最大工作集317,526,016→316,575,744字节。新48三轮CPU比为0.985294、0.941606、0.971014，逐配对中位0.971014（减少2.8986%），两侧中位比0.978102；逐配对solve墙时中位1.004624（增加0.4624%），完整CLI两侧中位2.3991→2.4046秒。小收益、运行间差异、用户背景与Win32 CPU时间量化均限制外推。

所有原始json/csv/failure、stdout/stderr、host ticks及summary冻结在`research/batch51/paired-completion.json`，SHA为`5ea14780ba5c41c8b1b9c7cd8731395908d76698f3ce80f1bdeecedd12486271`，成本schema为`reports/resource-cost-{hard,heldout,summary}-batch51.json`。离线汇总首次因Windows反斜杠路径KeyError退出，随后仅将汇总器路径键改为Path.as_posix再读取同一批raw；测量脚本未改、trial未重跑、无背景扣除。当前默认仍R48，等待父任务独立成本复核后决定推广；新的恢复本身不等于通用加速。


第51批当前默认：在R48基础上新增完整remaining-DIRECT用户祖先释放cut；Compute BEGIN W+O、最后原DIRECT消费者END释放、cut外用户/sink保留、原边和硬件/截止不改。2M新阶段来自原16M总预算，最多128节点/top24持出producer/单一确定性greedy，不增加种子或预算。原202困难144→145，新增140节点原图T1430270恰好deadline、peak2481<=2483；186共有成功T/peak恒等、0丢失，新48仍42/48，57+6共63已知可行未解显式保留。合计1349记录1286按预期通过，含1预期不可行拒绝与参数重复，不是1286合法可行输出。

候选实际1099条直接R48回归逐record相同（979+36+72+12），625固定计划/495闭包/83识别+210移动/102cut独立bigint及ClangUBSan通过。首次C盘ENOSPC构建exit1历史保留，仅编译子进程TEMP/TMP/TMPDIR改项目F-temp重试exit0，未清用户文件或改系统环境。推广后actual默认14/14 CTest（12.45秒共享功能）及10烟测7合法（4恢复+3正常）/3已知可行未解匹配已验收候选，未重新跑979或完整性能。

唯一同Release54fc→25ac完整202+48各3轮/12trial/1500case执行：困难全CPU比0.857803/0.937605/1.060692，paired中位-6.24%、side中位-6.07%，第三轮+6.07%保留；新48 CPU中位-2.90%，solve墙时+0.46%。每trial原始宿主CPU ticks/RAM起止+0.25秒采样均measured，包含用户背景、不扣除背景，非OS隔离，不称稳定通用加速。全部失败成本分组保留。actual默认EXE `c491f69d9ac2b39fa336afc5ef17b300bbdf84ab9021a482b3d404f91191b607` 与实测EXE `25ac71bc389e62f512d7597d40048e97b88783c21e895524cdba3311c6067742` 分开；源 `8b7c5383215084692b812a1451d1137802bf00323e80170ed5ce1ed14a1ecf4b`，清单 [provenance](research/batch51/provenance.json)。R48完整回退档在 `research/batch48/rollback/manifest.json`，用户旧R31打开TeX严格保持。R49扩组/50first pivot不混入默认；R50曾改善共同131峰1946→1884但0新增恢复，独立负结果仍保留。
