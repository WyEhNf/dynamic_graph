# VM 第一阶段：参数预解码

第一阶段只实现运行时 typed operands，仍使用原 `vector<double>` 栈和 switch 分派。普通发行版 `build/cholesky_runtime.exe` 的4f73、memory的7da0以及AVX-512实验d4e5均保持冻结。此阶段默认 `CHOL_PREPARED_VM=OFF`；即使研究构建启用，未传参数时仍执行 `legacy`。

研究构建位于 `build-stage2-vm-decode`，候选SHA为 `bf54f13b195f26547ded80dfd225f795062cfc427e2c3d1fb299c72010a96cdc`。使用方式为添加 `--vm-backend decoded`。只有实际进入VM的执行受到该参数影响；native认证及AUTO规则不变。原完整Metadata、符号图和PROGRAM不改写。

预解码只将LOAD/STORE/UNINIT的槽下标以及JUMP/JZ/JNZ的目标转换为整数字段。每个CONST和其他参数保留原double值。非法 immediate 记录为无效，直到原指令真正执行才按原顺序抛错；不提前拒绝未到达或未采用分支的坏目标。WRITE动态下标、未初始化读取、整数转换、有限输出及返回状态仍由原handler检查。每个原opcode执行前的步骤计数、错误检查顺序和4096栈上限保持原契约。

本阶段每个矩阵单独建立plan，没有M缓存。`vm_prepare_ms`记入总 `compute_ms`，`vm_plan_bytes_peak`记录plan实际保留容量，目前32字节/条。原槽、栈、输入和输出内存另外存在，该指标不等于进程总内存。`vm_steps`记录全部原指令步骤；失败路径的最后原PC由API指标验证。

## 已验收功能

| 验证 | 实际结果 | 证据 |
|---|---|---|
| 33 opcode/独立IEEE bitgold/错误顺序/直接构造坏Metadata/步骤与栈边界 | 404次legacy/decoded对照通过 | `artifacts/stage2-prepared-vm-phase1/native-contract.exe`、`tests/prepared_vm_tests.cpp` |
| 9类必须VM的真实C、43输入家族、尺寸3..129 | 172次完整原C文件字节通过；包含旧4f73、新legacy/decoded/默认 | `correctness/report.json` |
| int32溢出、INT_MIN/-1、转换越界、零除 | 7类CLI错误文本/退出码/partial清理与旧4f73一致 | 同上 `failures` |
| 原项目完整回归 | 9/9通过，150.47秒 | `ctest.log` |
| 真实显式fma/普通乘减/负零/subnormal/math builtin C | 四后端各167,412完整字节与原C一致，另核独立表达式golden | `fp-supplement/report.json` |

功能批允许与其他项目并发，所有时长只表述成本观测，不能用于加速归因。第一阶段已先冻结 `phase1-manifest.json`、候选EXE及103份实际源文件/CMake flags/测试文件到 `candidate-source/`。随后新增的FP与性能脚本单独保存在各证据目录，不覆写初次验收manifest。

## 后续预声明与当前限制

`maximum-shape/plan.json`的N10000 O(N²)一般while-copy源已实际完成，session47410 exit0。最初1.61GiB空闲不足而等待，后来恢复3.76GiB且每个后端启动前再次通过2.5GiB门槛：先真实原C产生磁盘参考，再顺序运行旧4f73及新三个模式，四份输出均核完800,000,008字节。源为动态while循环，逐位置读实际输入并写输出，没有数学/形状特判。原CPeakWS为1,605,013,504字节，四后端分别1,605,697,536/1,605,709,824/1,605,713,920/1,605,709,824；全过程最小可用RAM为1,899,819,008字节。

本源执行1,700,000,012个原opcode，超过原默认10^9；预声明显式预算10^10，默认没有放宽。新legacy/decoded/默认的步骤数完全相同，decoded plan为768字节。功能批的单次compute为旧4f73 14,766.1ms、新legacy 11,064ms、decoded 9,367.63ms、默认10,650.4ms，没有配对重复，不用它推定加速。完整来源/输入/参考/输出SHA和资源计数保留于 `maximum-shape/report.json`。

隔离性能计划为 `performance-v3/run-plan.json`，9类 `optimized=none` C源，每源5轮legacy/decoded交替，共90次。只按已冻结原步骤数重复完整M10输入流，目标每次至少4千万原步骤，避免按测得收益挑规模。参考各矩阵字节来自先前实际执行的原C完整输出，仅重写外层M计数。每trial核源、Metadata、输入、C binary/harness、参考与候选SHA，之后独立全文件比对。decode成本保留在compute，并列IO、读取、SHA及比对成本。

宿主用户应用没有关闭，项目测试批隔离不表示整机空闲。根释放窗口后v3实际执行session79341 exit0，共33.398秒，90次完整原C输出校验通过。Win32逐trial宿主busy为26.52%..53.07%，最小available为3,300,237,312字节；性能只限定为这次背景负载下的配对观测。SHA验证总1.819秒、文件逐字节对照总1.106秒单列，不计入runtime的compute。`performance/`及`performance-v2/`为执行前静态方案，前者没有宿主监控，第二版含静态CLI参数错误，均未运行；v3修正并冻结脚本/资源probe。

| 实际VM源 | legacy/decoded compute中位(ms) | 配对中位decoded/legacy | 五对完整比值 | decoded胜数 |
|---|---:|---:|---|---:|
| changed-arithmetic | 237.409 / 211.202 | 0.902282 | .895297,.946637,.942916,.889612,.902282 | 5/5 |
| changed-SSA | 232.141 / 204.376 | 0.905484 | .909357,.809879,.905484,.908930,.902956 | 5/5 |
| generic-if-while | 238.142 / 217.244 | 0.927862 | .883576,.947008,.927862,.923296,.955562 | 5/5 |
| int-arithmetic | 227.502 / 222.127 | 0.976374 | .976374,1.023996,.958457,.932751,1.025610 | 3/5 |
| int-conversion | 242.991 / 219.532 | 0.923187 | .927492,.897022,.923187,.885732,.957727 | 5/5 |
| deep-SSA40 | 270.376 / 236.261 | 0.858391 | .850965,.874090,.861154,.858391,.856007 | 5/5 |
| nested-helpers | 274.612 / 222.732 | 0.812120 | .799291,.821282,.863939,.787068,.812120 | 5/5 |
| SSA-conditional | 227.125 / 210.974 | 0.887706 | .887706,.854609,.930574,.997594,.882928 | 5/5 |
| unused-double | 274.652 / 234.723 | 0.887357 | .920259,.887357,.903208,.868079,.815228 | 5/5 |

共43/45对compute较低，整数运算的第1/4轮分别慢2.40%/2.56%，完整负值保留。9源配对中位下降约2.36%..18.79%，不是两个独立中位之比，也不是通用保证。单trial的prepare中位为.04.. .63ms、plan864..8512字节（另最大copy为768字节），已经包含在compute。小N单矩阵的固定开销没有在这次重复流吞吐计划中单独估计，不能据此声称所有短程序更快。普通Runtime和AUTO暂不晋升。

TOS缓存、初始化标志布局及computed-goto仍是后续独立阶段，未混入当前候选。不能由本地功能通过或未来速度变化推定官方85/15得分、任意C已支持或cubic N10000可实用完成。设计依据与适用子集见 `docs/stage2-runtime-audit.md`，primary链接与边界说明保留于审计。
