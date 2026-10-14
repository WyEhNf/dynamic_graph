# 参数化Metadata、源程序与任务图

2026-10-14本轮新增 `--symbolic-format packed`，编码名 `expr_dag_packed_records_v1`。`--smallest-metadata`现从schema 2/3 × dag/table/expanded/packed八种完整候选选择；平局仍先schema 2，再dag/table/expanded/packed。默认schema 2/dag保持。以下早期字节数字、构建哈希是各阶段冻结记录；当前安装版本见[本轮开发验收](development-2026-10-14.md)。

packed保留全部表达式和记录：`symbolic_expr_ops`存一次操作名，`symbolic_expr_pool`每节点首项改为操作名表的整数索引，其余参数与前向子引用保持。记录字段ID依次为 `id,kind,condition,increment,parent,mode,array,index,loop_ids` 的0～8；未知字段保留字符串。`symbolic_loop_records`及`symbolic_access_records`各为 `[字段ID/未知字段名数组,共享presence mask或null,行数组]`；所有行字段集合相同时共享mask，否则每行仍为 `[mask,values]`。字段缺失与显式null保持。

kind的for/while、mode的read/write、array的input/output分别编码为0/1；这些字段的其他实际值以 `['=',value]` 逃逸，包括整数、bool、null或数组，防止枚举与真实字面量混淆。完整解码函数为 `tools/packed_symbolic_metadata.py` 的 `unpack_symbols`/`decode_packed_symbols`。非法mask、重复字段、越界ID、bool ID、非法枚举等拒绝。前端写文件前做完整往返相等检查，没有删除PROGRAM、task_dependences或符号依赖。

运行时对schema 3的无参数单字符指令使用直接映射；带参数指令的数字文本用明确ASCII语法检查，再沿用原stream转换。浮点舍入、subnormal、参数位值与报错路径不改变。符号图在运行时仍属于受信编译器接口的审计描述，执行原完整PROGRAM或已有严格证明的Cholesky任务图；不宣称运行时重新验证全部审计图。

2026-10-14 05:55当前普通CLI/core为912c9fec/e7c9dd7f，已合入调用内联合扫描与owned结构化原地分解，206源码和已测产品对齐。新编译开关、复用计数与时间口径见文末“owned结构化路径指标”；下列03:24版本描述为历史栈证明进度，其能力继续保留。

2026-10-14 03:24当前普通CLI/core为4cceb9db/9b9d3e8a。`CHOL_PROVED_OPERAND_STACK`是构建开关：全局OFF、local-mingw ON、memory preset OFF。启用后只有immutable `PreparedVM`的GNU threaded session会一次认证实际完整PROGRAM的栈高度/控制流；原PROGRAM、schema、浮点参数位值和PC不重写，steps及固定预算继续逐指令检查。未知、超100k指令、分析分配失败均保留检查。认证位私有，只由owner首次发布，decode构造默认false；portable回退不运行这个无用认证。普通Metadata调用和CLI默认per-matrix不分析。编译依赖prepared+threaded VM，memory preset显式关闭该能力。

认证只许可省掉必然成功的栈/PC/opcode边界检查，不能许可移除数组索引、Trunc、初始化、WRITE有限性或返回状态检查。decoded记录保持16B，不声称总内存不增：分析临时heights/pending在100k指令上界约1.2MB，首次认证成本含在prepare/compute。显式session可按原用法调用，三组长流收益8.85%/4.25%/3.69%；冷M1/M2仍可增加数微秒，不自动选择session。项目回归用例为`tests/proved_operand_stack_tests.cpp`，通过`proved_operand_stack_contract`注册。

2026-10-13夜间新增显式 `PreparedSource` / `tools/analyze_batch.py`：同一翻译单元可生成多个函数或编码，每份使用独立Compiler状态。批准备先记录Clang实际源文件和全部头文件依赖，再对AST/IR编译前后依赖集合及内容哈希进行核对；源、头文件、编译器状态或环境改变时拒绝复用。六输出批次由12次Clang调用降至3次，三对实测耗时中位4931.56→1468.68ms，配对降幅中位70.15%。这是批量分析收益，普通单次完整审计仍为两调用，该次测量中位反而慢3.48%。

默认保留完整LLVM审计IR。显式 `--skip-ir` 只省略 `.ll`，完整符号图、PROGRAM和来源仍保留，分析报告写 `ir=null`、`ir_status=omitted-explicitly`；单次筛选配对降幅中位48.42%。若目录已有旧 `.ll`，报告不会将它关联到本次结果。批CLI的jobs输入、源和依赖、各份Metadata/分析/IR及可选report之间有写入路径冲突检查。

批任务JSON为数组，例如：

```json
[
  {"function":"cholesky","output":"default.meta"},
  {"function":"cholesky","output":"small.meta","options":{"smallest_metadata":true}}
]
```

```powershell
.venv\Scripts\python.exe tools\analyze_batch.py fixtures\official_naive_transcribed.c --jobs jobs.json --clang 'C:\Program Files\LLVM\bin\clang.exe' --report batch-report.json
.venv\Scripts\python.exe tools\analyze_source.py fixtures\official_naive_transcribed.c --function cholesky --output artifacts\metadata-only.meta --skip-ir
```

集中验收包含168次原C全文件对照、36份完整图与36份数值位检查、46份既有默认文件审计、13项快照/CLI控制；随后仅对新增输出保护补8项拒绝及1项正常CLI检查。源码已安装，证据与回滚位于 `G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/`。见[阶段指标](stage-metrics-2026-10-13.md)。

2026-10-13起新生成文件默认使用LF换行，`--metadata-newlines native`可恢复宿主换行。schema和完整图/PROGRAM保持原规则。六个测试源默认schema2总体积10,724→10,046字节；以下旧体积数字为Windows CRLF历史冻结记录。见[本轮阶段指标](stage-metrics-2026-10-13.md)。

UTF-8格式第一行为 `DYNCHOL 2`，`key=value`头部后以 `PROGRAM` 开始栈字节码。Runtime检查关键字段、指令/操作数、参数槽、数组对象与跳转目标；未定义整数行为、非法访存或指令限额均失败。

新增的schema 3通过`--metadata-schema 3`显式选择；默认仍为schema 2。它保留同一`ast_vm_v2`语义、全部符号图和`task_dependences`，只改变PROGRAM的操作码文本。第一行必须为`DYNCHOL 3`，并带唯一的`bytecode_encoding=base36_opcode_v1`。新Runtime向后兼容schema 1/2，旧Runtime应拒绝schema 3。v2文件带此编码字段亦拒绝，防止跨版本误解码。没有根据文件内容猜编码的别名路径。

## 可选的表记录和opcode编码

`--symbolic-format table`选择`symbolic_encoding=expr_dag_record_table_v1`。表达式池不变；`symbolic_loop_table`和`symbolic_access_table`分别存`[字段名列表, [[presence_mask, 已存在字段的值列表], ...]]`。mask的低位对应首字段，值按字段顺序排列；缺失字段与显式null保持区别。还原记录后再解表达式DAG，即得到完整的原始符号图。重复字段名、mask越界、bool mask、值数与置位数不同均拒绝。前端生成时执行完整往返检查；这是审计图编码，Runtime的信任边界仍为受信前端。

schema 3的固定映射依次为下列33个操作码，对应字符`0123456789ABCDEFGHIJKLMNOPQRSTUVW`，与C++枚举的数值无关：

```text
CONST LOAD STORE UNINIT READ WRITE DUP POP
ADD SUB MUL DIV IDIV MOD NEG NOT BOOL TRUNC SQRT ABS MIN MAX FMA
LT LE GT GE EQ NE JUMP JZ JNZ RETURN
```

每行一条指令，有参指令为`单字符ID + 一个ASCII空格 + 原始参数文本`，无参指令仅有单字符ID。数字允许十进制、前置正负号和十进制指数，必须有限；操作数文本、负零、指令顺序和跳转下标均保留。无参opcode的显式0、前后多余空格、额外token、未知字符、错误/缺失encoding字段均拒绝。`--full-bytecode-args`仅适用于schema 2，与schema 3组合由前端拒绝。原有槽/数组/jump范围和100000指令上限保持。

```powershell
.venv\Scripts\python.exe tools\analyze_source.py fixtures\official_naive_transcribed.c --function cholesky --output artifacts\official-wire.meta --symbolic-format table --metadata-schema 3
build-stage2-wire\cholesky_runtime.exe --metadata artifacts\official-wire.meta --input artifacts\synthetic-input.bin --output artifacts\wire-result.bin
```

这一设计参考[LLVM官方bitcode文档的record缩写思想](https://llvm.org/docs/BitCodeFormat.html#abbreviations)：用紧凑记录标识减少重复文本。本项目使用自定义UTF-8协议和固定表；没有引入LLVM bitcode依赖，也没有借用其性能结论。独立的Python/C++ literal golden测试核对全部33项，不由待测映射生成预期。

`artifacts/stage2-metadata-wire/report.json`保存新Runtime及源码SHA，五种实际C源、两个数据族、schema 2 dag/table和schema 3 table的60次VM/tiled全文件原C对照，以及图和解码后的PROGRAM相等检查。左看/官网右看/自设分块从默认dag的2250/2655/3739字节降至1719/1934/2626字节（约23.6%/27.2%/29.8%）；相对table还减少15.6%/16.8%/20.2%。小程序未必受益：表头和encoding字段有固定成本。测量为Metadata原始文件字节，不能据此推算官网15分，也不声称算术kernel加速。

固定成本的实测反例为`noop`常量返回C源：v2 dag/table为306/338字节，v3 dag/table为324/356字节；四种版本均对照原C全文件通过。见`artifacts/stage2-metadata-wire-overhead/report.json`，协议开销使该极小程序增加18字节，默认不改可避免强制损失。

`--smallest-metadata`显式选择文件最小策略。前端只运行一次实际AST编译和一次LLVM IR生成；从同一Compiler对象及同一符号图产生schema 2/3 × dag/table/expanded六个UTF-8候选，按实际发出字节数选最小。所有候选保留完整图/参数/PROGRAM/依赖；没有删审计图来减文件。平局先schema 2，再dag/table/expanded；`.analysis.json`列出各候选字节数和SHA及最终schema。CLI与显式`--metadata-schema`（即使2）、`--symbolic-format`（即使dag）、`--full-bytecode-args`互斥并报错，避免静默覆盖。`--provenance-inline`可组合，追溯字段同样保留在所有候选。由于可能选schema 3，此策略要求更新Runtime；默认不启用。

```powershell
.venv\Scripts\python.exe tools\analyze_source.py fixtures\official_naive_transcribed.c --function cholesky --output artifacts\official-smallest.meta --smallest-metadata
```

`artifacts/stage2-smallest-metadata/report.json`独立保存六源、各自六个显式候选的完整还原相等检查、原默认字节及实际最小选择，以及24次VM/tiled原C全文件对照。测试记录每次最小策略恰为一AST和一IR编译；测试为了提供独立候选文件大小，另外编译了六个显式版本，此成本不属于生产最小策略。普通三源选v3 table 1719/1934/2626；通用控制源选897；负零源选v3 dag 619（原667）；noop选v2 expanded 284（原306）。这些源均比旧默认小，不据此声称任意源码有正收益。因旧默认也在候选集合内，文件最小值的“不大于同一次编译的旧默认”由枚举本身保证。

新Runtime完整8/8 CTest通过（160.93秒），其中既有schema 2的405次全文件比较/53拒绝保持；schema 3的60次源码对照另列。原生12项解析bit golden直接核对两个schema下的+0/-0、5e-324、最小normal、最大有限数及9007199254740993.0的IEEE754结果，见`artifacts/stage2-metadata-wire-native-boundaries/report.json`。另外七个边界常量分别在v2/v3执行WRITE，14个全文件独立bit golden通过，见`artifacts/stage2-metadata-wire-numeric-bits/report.json`。

最小策略引入共享渲染逻辑后，`artifacts/stage2-default-metadata-audit/report.json`又核验四类full流水线所有46个已接受Clang分析产物的source SHA，并重新生成默认schema 2/dag Metadata，46个完整文件字节均与此前流水线相同，零跳过（60.64秒）。这项覆盖前端默认渲染回归，未重复昂贵的原C和Runtime计算；源码及Runtime数学执行链没有因最小策略修改。

| 字段 | 语义 |
|---|---|
| `algorithm=ast_vm_v2` | 实际Clang AST产生的可执行源程序 |
| `arithmetic=fp64_source_order_no_implicit_fma` | FP64源算式和逐位置运算次序；显式fma为单独指令 |
| `dependencies=source_control_flow` | 未证明可变换的程序保持源控制流 |
| `optimized` | 完整符号运算图证明后允许左看/右看/连续分块Cholesky，否则none |
| `slots/shape_slot/block_slot` | 按声明身份取得的标量槽；运行时绑定N及可选源block |
| `symbolic_encoding/symbolic_expr_pool` | 共享符号表达式DAG，子引用严格向前；expanded可选 |
| `symbolic_loops/symbolic_accesses` | 循环域/递增/父循环、数组读写参数化下标及所属循环 |
| `task_schema/task_dependences` | 已证明源的参数化任务域与依赖；不存在固定N节点表 |
| `source_sha256/function` | 可选内嵌追溯；默认移至analysis.json，不参与算法选择 |

字节码有参数的CONST/LOAD/STORE/UNINIT/READ/WRITE/JUMP/JZ/JNZ保留操作数，其他操作码默认省略冗余0。Runtime兼容早期v2的显式0；缺失必须操作数、无参opcode带非零操作数或多余token拒绝。`--full-bytecode-args` 面向较旧v2 Runtime。分析JSON始终记录原source和Metadata SHA及展开的符号图。

相同Metadata处理N3..10000和不同源码block。改变算式会改变实际程序；不满足证明的变化执行VM，不能靠函数名/hash回退固定结果。纯标量helper支持顺序初始化不可变SSA局部值，类型转换保留；mutable/control-flow helper拒绝。有符号int32算术和浮点转int检查范围，除余零和INT_MIN/-1拒绝；整数零归一为+0，FP64符号零保持。

优化证明匹配声明身份、完整循环域/访存/算术数据流。连续分块包装只有在正block步进和截断边界覆盖相同递增整数域时可消去。整数地址交换和等价边界可规范化，浮点归约不作代数交换/重排。Python -O不会关闭证明检查。

相邻单变量声明与末尾递增的计数型while仅在证明视图规范化为for；实际可执行字节码与审计循环保留while。仍检查完整初始化、条件、步长、访存与全部运算；变步长或变算式不满足证明时继续VM。63次独立C对照覆盖左/右看、显式fma及动态分块1/7/32/100。

## 可选完整文件压缩容器

`--compress-metadata`将已选择的完整UTF-8 Metadata包进`DYNCHZ01`容器；不删除图、PROGRAM、参数文本或任务依赖，也不参考源hash或N。前端默认仍输出普通schema 2。容器是8字节ASCII magic、little-endian uint32解压长度、uint32 zlib流长度，再接一个[RFC1950](https://www.rfc-editor.org/rfc/rfc1950)流；其内部DEFLATE遵守[RFC1951](https://www.rfc-editor.org/rfc/rfc1951)。16字节容器头之外，zlib流含2字节格式头和4字节Adler-32校验。校验用于损坏检测，不提供来源认证。

解压长度及压缩流各限16 MiB（原文非空，流至少6字节），原生读取先限制文件长度后分配。仅允许一个无字典的zlib流，验证结束状态、准确消费字节、准确输出长度与Adler-32；尾随数据、串联流、gzip/raw-DEFLATE、字典、损坏或截断、超限均拒绝。解压后使用既有DYNCHOL1/2/3文本解析器；嵌套容器和错误内层版本/字段/指令不能绕过解析。16 MiB界限只适用此新容器，普通文本格式的旧上限不变。

独立`build-stage2-zlib`启用`CHOL_COMPRESSED_METADATA=ON`，以未修改的[官方zlib 1.3.2](https://zlib.net/)源码静态链接；默认选项OFF，普通已发布build EXE保持冻结。`third_party/zlib-1.3.2`包含原始源码和LICENSE，`artifacts/stage2-metadata-zlib/zlib-1.3.2.zip`及dependency-provenance记录官方下载URL、发布SHA与全部文件SHA。CMake不需要网络或额外zlib DLL；迁移机器仍需已有C++工具链运行库。FP64的`-fno-fast-math -ffp-contract=off`及AUTO块规则保持。

```powershell
cmake --preset local-mingw -B build-stage2-zlib -DCHOL_COMPRESSED_METADATA=ON -DCHOL_PACKED_READY_KEYS=OFF
cmake --build build-stage2-zlib --parallel 2
.venv\Scripts\python.exe tools\analyze_source.py fixtures\official_naive_transcribed.c --function cholesky --output artifacts\official-compressed.meta --smallest-metadata --compress-metadata
build-stage2-zlib\cholesky_runtime.exe --metadata artifacts\official-compressed.meta --input artifacts\synthetic-input.bin --output artifacts\compressed-result.bin
```

与`--smallest-metadata`组合时，从同一次AST编译和LLVM IR生成取得schema2/3 × dag/table/expanded六个完整等价候选，逐个编码完整容器，按最终实际传输字节数选最小。平局先schema2，再dag/table/expanded；不用原文大小作为压缩候选的排序键。只启用未压缩最小策略时仍按原UTF-8大小；显式单一schema/格式加压缩只压缩该指定格式。两个参数都为显式opt-in，旧普通Runtime不能执行容器。`.analysis.json`记录每个候选的最终及原文大小/SHA、获选schema/格式、成本指标及tie规则。六候选取最小仅涉及该集合，不声称对所有压缩算法或格式全局最优。

57个冻结Metadata实测按全部开销计：六个原最小文件scalar/page/blocked/generic/negative-zero/noop分别从1719/1934/2626/897/619/284降到760/763/958/492/407/225字节。noop在本测量中亦有收益；空、不完整头与256字节高熵非Metadata样本仍记录容器膨胀，不能承诺任意文件缩小。`size-probe.json`保留全部候选，不丢较大者。原生与Python标准zlib交叉检查42个六源编码的完整解压字节，七种标准DEFLATE模式、原始/压缩16 MiB合法界限、最小1字节容器和12个native IEEE754位golden另测。原C独立重新编译的72次完整结果比较，覆盖两个数据族、三个实际编码、VM/tiled及N3/7/17/31/33/65/127；见`validation/report.json`和新CTest冻结报告。

第一版“先原文最小再压缩”的72次验证中，`metadata_read_ms`包含文件读取、解压和原文本解析，观察中位1.5345 ms、范围0.433..6.910 ms；它与`compute_ms`分别记录，未做受控加载性能对照。第一版完整来源、9/9 CTest和上述数据由`artifacts/stage2-metadata-zlib/manifest.json`冻结，旧文档和报告保持原版本。

当前组合改为最终容器字节最小后，scalar/page/blocked/generic/negative-zero进一步从760/763/958/492/407降到731/735/912/481/397字节，均选schema3 expanded；noop保持225字节，选schema2 expanded。这里的expanded原文可能比table更大，完整树的重复内容经通用无损压缩后更短，六个原文和容器候选都留存。`artifacts/stage2-compressed-smallest/report.json`核验36个完整候选的图/PROGRAM/依赖等价与native解码，实际frontend组合每源恰一AST和一IR；六源的未压缩默认及原最小字节保持，单格式压缩亦验证。当前选中文件另与独立重编译原C做两个数据族、VM/tiled共24次完整结果比较，普通4f73 Runtime及压缩ee3f Runtime均未改动，无新计算性能批。压缩节省Metadata字节，不能由此推算官网15分或计算kernel加速。

## 参数化P/T/U块DAG

物理B独立于源block，t=ceil(N/B)。节点为P(k)对角分解、T(m,k)三角求解、U(m,h,k)尾部更新。域为0<=k<t、k<m<t、k<h<=m<t；任务数t(t+1)(t+2)/6。依赖：

- P(k)依赖U(k,k,k-1)。
- T(m,k)依赖P(k)及U(m,k,k-1)。
- U(m,h,k)依赖T(m,k)、T(h,k)及U(m,h,k-1)。

域外依赖省略，对角的重复T仅计一次。每节点8字节状态，后继用闭式索引计算，不分配每节点边vector。就绪队列只释放依赖满足的任务；每输出位置的源k归约严格递增。因子按块内列打包，64字节对齐；P/T立即产生packed因子，U同时维护独立输出累加器。AVX2两行共享因子载入仍保持每个位置乘加链，非融合为独立mul/add、显式fma用fmadd。

研究候选按实际worker数选择物理B：单线程N<=1536用32，多个线程N<=1024用32，>=8线程且N>=4096用96，其余64；CLI `--tile-size auto|1..1024` 可覆盖。AVX2行主序路径按N>=2048选四行×八列，否则两行×十六列，独立位置仍各自保持k链。八行×四列为收益负的独立编译实验。heap默认，bucket实验；选择通知只在释放任务或全部完成时唤醒，错误唤醒全部worker退出。默认关闭的研究选项 `CHOL_LAZY_TILE_GRAPH` 为每目标块保存一个当前panel状态，常驻O(t²)、逻辑执行仍O(t³)；heap/bucket418次原C比较及30项失败生命周期已通过，104次性能保留规模/线程负结果。1600万逻辑任务上限仍显式拒绝。默认及memory配置已按最终preset重建，native优化冻结。

默认关闭的 `CHOL_COLUMN_WORKSPACE` 将下三角累加区和因子块合并为 tile-major、块内 column-major 连续工作区。它使用相同P/T/U依赖及每位置递增k归约，初始正零不可省略；P/T只重排独立位置，乘法操作数顺序亦保留。全部任务和worker完成后导出下三角到完整行主序L，上三角仍正零。209项独立原C比较及94次性能已通过，较大规模/多线程未稳定收益；实验保持OFF。另有默认OFF的 `CHOL_ROW_TILE_WORKSPACE` 用行累加块在P/T完成后转成列因子，`CHOL_TRANSPOSE_EXPORT` 批量转置和并行导出；418次原C比较、188次四构建对照证明导出局部收益，但计算总量与峰值RAM未稳定降低。JSON新增 `workspace_layout` 和 `export_ms`，`kernel_ms` 排除导出，`compute_ms` 包含导出；全L仍提前分配，不能声称峰值RAM降低。Metadata格式/语义不变，不依据源码hash或N标签替换数学结果。

`--engine vm`保持源串行，`stage`保留旧列屏障路径，`tiled`请求块任务，`auto`在受支持图且N>=128时使用块任务。识别图后默认先读取实际下三角，确认确切半带宽w<=128且4w<N，才可带状专门化；w=0为对角。`--structure dense`关闭结构路径，`--band-limit 0..1024`覆盖半带宽上限。只跳过初始+0归约的结构零前缀，其余k含实际零全部保留；保留带外符号零，显式FMA下溢后不省略零项。结构路径当前串行，worker指标为1；完整输入/输出布局仍为O(N²)，不依据N或hash查表。

helper重复/未使用局部值与参数按一次顺序求值，先计算全部参数再存callee槽；嵌套同helper和前向prototype按真实声明身份处理。有限SSA支持不等于所有helper可用native图：存在未使用求值、int局部值或一般int参数运算时保守留VM，避免丢失范围检查。唯一已证整数helper例外：两个int参数、无局部值、直接比较并直接选择其中一个参数，实际参数亦须int；调用参数的全部表达式仍参加完整native图证明。纯min分块for/while/FMA105次C对照＋12溢出拒绝，转换或int局部拷贝形式仍留VM。Metadata限4096槽和100000条指令，符号表达式另有限额。

本格式是受信本地编译器/Runtime契约，并非官网指定格式；Runtime不重新完成通用符号证明。保持旧DYNCHOL1兼容读取。Metadata评分当前只报原始文件字节，不制造15分归一化成绩。

研究生命周期扩展：`execute(const Matrix&,...)`保持输入不变，CLI改走按值拥有的`execute_owned`并移动vector，输入销毁计入compute。默认OFF的`CHOL_REUSE_INPUT_BUFFER`要求列块工作区，任务数学不访问完整L；所有worker退出及完成断言后将输入存储交换到结果，上三角填正零并完整导出下三角。第一阶段仅显式dense，418+100原C对照、36失败、API const/owned allocation身份通过；N10000同源hybrid对照峰值约2.02→1.22GB，M3峰值不随M倍增。吞吐包含单轮负值，export清零成本增加；并非相对历史row内核的单因素加速。auto扩展另有源码/二进制/测试快照：结构分类前不分配L，只有实际带状/对角证明成功后才分配其完整L；分类失败的native图可复用A，VM/stage/const保持旧分配。auto阶段854原C比较、288拒绝/42失败、74性能均通过。最终`local-mingw`保守row默认、显式`memory-mingw`资源配置；ordinary10k单线程和M3t4负值保留，不保证普遍吞吐收益。

`CHOL_VECTOR_SCANS`以整数FP64指数位判有限、绝对值位判断非零，portable退回标量；完整A包括上三角均先检查。545原C比较、288拒绝、308880位/保护页单测通过，60性能同源扫描批保留普通dense负值；带状N10000 auto compute167.145→147.255ms，结构扫描30.885→17.077ms，是局部结果。`input_validation_ms`为compute子项；M输出中的engine/layout/scan名称指最后矩阵，时间和复用计数按M累加，峰值取max，不能由最后engine推断每一矩阵的分派。

## 2026-10-14运行时更新（当前状态）

当前local-mingw和已安装1afefead运行文件启用column/row-tile工作区、transpose导出、owned输入复用及首任务初始化；上述“默认OFF”描述属于历史实验记录。原tile几何、每位置k归约次序及完整Metadata/PROGRAM保持不变。CLI完全不传执行参数时仍serial/1线程；engine默认AUTO不等于自动开启多线程。

`--worker-context auto|off`默认auto，仅M>1且显式parallel、多线程时创建流拥有的工作线程上下文，初始化和最终join计入compute。每个矩阵仍拥有独立任务状态和输出，复用线程不保留矩阵结果。

`--vm-plan per-matrix|session`默认per-matrix。显式session持有不可变Metadata快照，实际选择typed VM时才一次解码；每次执行的标量状态、栈、输出及N/block预算证明仍独立。内部解码记录现为16字节，`vm_plan_bytes_peak`只统计解码vector容量字节，不能代表完整Metadata或进程RAM；磁盘schema和原指令编号不变。

`--native-workspace off|session|session-trim`默认off；local-mingw明确编译该能力，全局`CHOL_CACHE_NATIVE_WORKSPACE`仍默认OFF。显式session只缓存64字节对齐因子容量，每次执行同步持有独立lease，首次任务重新清零有效累加单元；不缓存输入、输出或浮点环境。session-trim额外在带状/对角证明成功后释放此时不用的容量，接下来的dense可能需要重新分配，适合优先控制RAM的流。owned调用在这之前尚未分配完整L，borrowed调用已提前分配，二者不能套用同一峰值降幅。共享owner时close可能等待其他lease，资源比例只代表已测顺序CLI流。

`workspace_allocations/reuses`为流计数，`workspace_capacity_peak_bytes`为历史持有容量峰值，`workspace_release_ms`仅最终CLI释放；中途trim仍计入完整compute，但未单列该字段。`native_workspace_mode`报告请求模式。API的`NativeWorkspace()`默认false策略，`NativeWorkspace(true)`为不可变trim策略；默认构造保持非显式，布尔构造保持显式。尺寸变小时session可能保留容量并增加RAM，session-trim可能增加后续重新分配成本；冷单图和部分长流有负收益，二者均不改变默认AUTO策略。
## 2026-10-14 05:55：owned结构化路径指标

local-mingw开启 `CHOL_FUSED_FINITE_BAND_SCAN` 与 `CHOL_REUSE_STRUCTURED_INPUT`，全局默认和memory preset均OFF。既有native tiled结构分类成功后，CLI的私有owned矩阵可原地分解，带外正负零保留，计算完成后清上三角为正零再交换结果所有权；借用 `execute(const Matrix&,...)` 保持输入不变。没有新增Metadata字段或运行时选择参数，默认engine/plan/workspace/scheduler保持已有值。

联合扫描时间仅计入 `input_validation_ms`，名称为 `avx2_combined_finite_band`；复用事实的 `structure_scan_kernel` 为 `avx2_combined_finite_band_reused`，其 `structure_scan_ms` 不重复记同一时间。结构化owned的 `input_buffers_reused` 也计入复用数，`input_recycle_ms` 覆盖upper清零与swap，`kernel_ms` 覆盖factor数学；只有总 `compute_ms` 可用于与旧分项范围不同的版本比较。每流最后矩阵的名称/shape与按M累加时间、复用数及peak区别不变。

