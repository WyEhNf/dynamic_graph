"""Editable report source. All result tables are derived from retained evidence."""
from pathlib import Path
import datetime,hashlib,json,math,os,statistics,xml.sax.saxutils as xu
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,KeepTogether
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing,Rect,String,Line
ROOT=Path(os.environ.get('PROJECT19_REPORT_ROOT',str(Path(__file__).resolve().parent)))
if not (ROOT/'full-test/report.json').exists():ROOT=Path('G:/Hackathon-stage2-artifacts/project19/20261014-exploration')
P=Path('F:/Hackathon/projects/19-dynamic-graph')
OUT=ROOT/'output/pdf';OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
full=read(ROOT/'full-test/report.json');supp=read(ROOT/'full-test/supplement.json');bench=read(ROOT/'industry-benchmark/report.json');scale=read(ROOT/'scale-test/report.json')
structured=read(ROOT/'structured-test/report.json')
encoding=read(ROOT/'encoding-test/report.json')
assert all(x.get('passed') for x in (full,supp,bench,scale,structured,encoding))
stages_path=P/'artifacts/project19-stage-metrics-2026-10-13.json'
if not stages_path.exists():stages_path=ROOT/'historical-provenance/project19-stage-metrics-2026-10-13.json'
stages=read(stages_path)
S33=Path('G:/Hackathon-stage2-artifacts/project19/20261013-overnight/structured-owned-reuse')
screen_path=S33/'screen/report.json'
if not screen_path.exists():screen_path=ROOT/'historical-provenance/s33-screen/report.json'
screen=read(screen_path)
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/msyh.ttc',subfontIndex=0));pdfmetrics.registerFont(TTFont('CNBold','C:/Windows/Fonts/msyhbd.ttc',subfontIndex=0))
pdfmetrics.registerFontFamily('CN',normal='CN',bold='CNBold',italic='CN',boldItalic='CNBold')
navy=colors.HexColor('#173454');blue=colors.HexColor('#2e6489');grid=colors.HexColor('#b9cedd');grey=colors.HexColor('#75818b')
styles={
 'body':ParagraphStyle('body',fontName='CN',fontSize=9.5,leading=15.2,spaceAfter=7,wordWrap='CJK',textColor=colors.HexColor('#20272d')),
 'h1':ParagraphStyle('h1',fontName='CNBold',fontSize=13,leading=20,spaceBefore=10,spaceAfter=10,textColor=navy,keepWithNext=True),
 'h2':ParagraphStyle('h2',fontName='CNBold',fontSize=11,leading=17,spaceBefore=8,spaceAfter=7,textColor=blue,keepWithNext=True),
 'small':ParagraphStyle('small',fontName='CN',fontSize=8.0,leading=12.2,spaceAfter=5,wordWrap='CJK',textColor=colors.HexColor('#5b6771')),
 'cell':ParagraphStyle('cell',fontName='CN',fontSize=7.4,leading=10.9,wordWrap='CJK',textColor=colors.HexColor('#20272d')),
 'headcell':ParagraphStyle('headcell',fontName='CNBold',fontSize=7.5,leading=11.3,wordWrap='CJK',textColor=navy),
 'cover':ParagraphStyle('cover',fontName='CNBold',fontSize=21,leading=34,alignment=1,textColor=navy),
 'subtitle':ParagraphStyle('subtitle',fontName='CN',fontSize=15,leading=25,alignment=1,textColor=blue),
 'center':ParagraphStyle('center',fontName='CN',fontSize=10,leading=18,alignment=1,textColor=navy),
 'code':ParagraphStyle('code',fontName='CN',fontSize=8,leading=12.2,wordWrap='CJK',leftIndent=8,backColor=colors.HexColor('#f6f8fa'),borderPadding=7,spaceAfter=9)}
story=[];content=[]
def clean(t):
 t=str(t).replace('ᵀ','^T')
 for c in '\u2010\u2011\u2012\u2013\u2014\u2015\u2212':t=t.replace(c,'-')
 return t
def esc(t):return xu.escape(clean(t))
def para(t,style='body'):
 t=clean(t);story.append(Paragraph(t,styles[style]));content.append(dict(type=style,text=t))
def h(t,level=1):para(t,'h'+str(level))
def table(headers,rows,widths=None):
 cells=[[Paragraph(esc(v),styles['headcell' if i==0 else 'cell']) for v in row] for i,row in enumerate([headers]+rows)]
 t=Table(cells,colWidths=widths or [WIDTH/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.35,grid),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf3f8')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
 story.append(t);story.append(Spacer(1,8));content.append(dict(type='table',headers=headers,rows=rows))
def page():story.append(PageBreak())
def code(t):
 text=esc(t).replace('\n','<br/>');story.append(KeepTogether([Paragraph(text,styles['code'])]));content.append(dict(type='code',text=text))
def fmt(v):return f'{v:,.3f}'
WIDTH=A4[0]-104
class Report(SimpleDocTemplate):
 def afterFlowable(self,f):
  if isinstance(f,Paragraph) and f.style.name in ('h1','h2') and f.getPlainText()!='目录':
   level=0 if f.style.name=='h1' else 1;text=f.getPlainText();key='heading-'+str(self.seq.nextf('heading'))
   self.canv.bookmarkPage(key);self.canv.addOutlineEntry(text,key,level,False);self.notify('TOCEntry',(level,text,self.page,key))
def footer(c,d):
 c.saveState();c.setFont('CN',7.5);c.setFillColor(grey)
 c.drawString(52,29,'19题探索报告 | S33冻结版 | 2026-10-14');c.drawRightString(A4[0]-52,29,str(d.page));c.restoreState()
def bars(rows,title,maxv=None):
 d=Drawing(WIDTH,30+25*len(rows));d.add(String(0,d.height-11,title,fontName='CN',fontSize=8.6,fillColor=navy));mx=maxv or max(v for _,v in rows)
 for i,(label,v) in enumerate(rows):
  y=d.height-40-i*25;d.add(String(0,y+4,label,fontName='CN',fontSize=7.5,fillColor=navy));w=max(1,200*v/mx)
  d.add(Rect(180,y,w,14,fillColor=blue,strokeColor=None));d.add(String(185+w,y+4,f'{v:.2f}',fontName='CN',fontSize=7.4,fillColor=navy))
 story.append(d);story.append(Spacer(1,7))

story.append(Spacer(1,126));para('动态 Shape 算子图与运行时','cover');para('第19题完整探索报告','subtitle');story.append(Spacer(1,27))
para('全量回归 · 同机业界对照 · 探索过程与复现','center');story.append(Spacer(1,43))
para('评估对象：当前已安装 S33 版本','center');para('报告日期：2026年10月14日（北京时间）','center');para('项目位置：F:/Hackathon/projects/19-dynamic-graph','center');story.append(Spacer(1,30))
para('证据类型：本次新执行测试 / 历史冻结实测 / 一手文献 / 条件性判断','center');para('本地显式源码契约；无官方隐藏测试及正式评分结果','center');page()
para('目录','h1');toc=TableOfContents();toc.levelStyles=[ParagraphStyle('toc0',fontName='CN',fontSize=9,leading=13,spaceBefore=4,textColor=navy),ParagraphStyle('toc1',fontName='CN',fontSize=8.0,leading=11.2,leftIndent=14,textColor=blue)];story.append(toc);page()

h('1 执行摘要与证据边界')
para('当前成果是一个面向受支持 C 源码的语义保持编译前端与动态 Shape 运行时。它把源码转为共享表达式 DAG、紧凑 PROGRAM 和算子依赖 Metadata，对已证明等价的 Cholesky 模式使用参数化原生任务图，对其余受支持程序使用 VM。核心价值在于保留指定 C 程序的浮点计算顺序，同时利用独立单元并行、SIMD 和生命周期优化。')
table(['结论维度','本次结果','解释'],[
 ['当前构建回归','local 15/15；memory 10/10；Python 3/3','两套实际 preset 全新构建；无失败、无跳过。'],
 ['独立源码真值','810次完整文件比较；106项预期拒绝','基础188、helper49、while63、整数选择105，各配置各执行一次。'],
 ['结构与Metadata补充','760次结构源码＋48次Metadata变体对照','两配置各完整380条结构集合；全部独立C全字节通过。'],
 ['最小编码与功能门','48次独立C对照；12项预期拒绝','schema2/3 × dag/table/expanded，单次AST/IR最小选择；关闭的压缩输入拒绝。'],
 ['最大规模补充','24次基准原生运行＋5次规模验证','所有29次当前 CLI 输出满足完整真值比较；覆盖 N10000、混合 Shape、session/trim 和兼容构建。'],
 ['普通 dense 性能','N10000 whole compute：11.109 / 3.375 / 3.338秒（1/4/16线程中位）','对照 OpenBLAS 包装计时约慢1.90 / 1.70 / 2.07倍；采样受宿主波动影响。'],
 ['结构化性能','S33四组 compute 中位下降76.46%–82.16%','相对上一冻结产品的配对实验；不是普通 dense 同幅加速。'],
 ['数学精度与位一致','OpenBLAS因子相对误差约1.2e−16，但 dense 下三角约68%–70%位值不同','成熟库很快且数值接近，但不能直接替代指定 C 全字节契约。'],
 ['综合定位','有明确语义约束的研究型编译／运行时原型','已超过简单标量或 VM 演示；尚无依据宣称达到通用 BLAS 性能或官方领先。']], [83,185,WIDTH-268])
h('1.1 事实、历史结果与推断',2)
para('本次测试于 2026-10-14 新执行，冻结源文件共206个。已安装 EXE 的 SHA256 为 912c9fec…9072eba，核心静态库为 e7c9dd7f…3b3c6。全新 local 构建的9个核心对象和 main 与生产对象字节一致；完整 PE 仅时间戳、校验和不同。测试结果可归属当前版本，而非旧目录中遗留的测试 EXE。')
para('报告中 S1–S33 的性能来自各阶段原始冻结记录；没有把独立阶段比例相乘，也没有把旧版本样本冒称为本次重测。本次 OpenBLAS 的48个进程是新的同机实验。文献仅提供设计和 benchmark 背景，未执行的框架不列为同机成绩。')
para('没有官方测试包、正式 CPU／线程约束、div/madd helper 完整定义和完整官方分块源。因此“全部通过”仅指已列明的本地测试集合，不能证明任意合法 C、任意 CPU、官方隐藏集或最终得分均通过。对性能上限和后续方向的评价属于条件性判断。')

h('2 赛题拆解与抽象建模');h('2.1 实际要建模成什么问题',2)
para('问题可抽象为：在动态参数域内，对带浮点顺序、内存访问和控制流约束的程序进行依赖分析，生成一个可复用的参数化执行表示，再寻找满足逐位等价和资源约束的最低成本调度。Cholesky 是当前优化对象，真正的建模对象是“有序计算的依赖图与运行时调度”。')
para('设源码 P、动态 Shape n、输入 A、调用环境 E；C 参考执行为 R(P,n,A,E)。要求输出二进制序列 B 与 R 的全文件字节相同，同时最小化 T_compute，并约束 Metadata 大小、工作内存、线程数、失败行为。数学等价 A≈LLᵀ 只是必要背景；它不替代 B=R 的程序语义条件。')
table(['模型层','状态／约束','主要难点'],[
 ['前端分析','AST类型、纯 helper SSA、表达式 DAG、地址／循环域','证明完整操作链；函数名或源码 hash 不足以授权快径。'],
 ['数值依赖','每个单元按原始 k 次序累加；除法／sqrt／显式 fma 保留','分块、并行及 SIMD 不能偷偷重结合或融合。'],
 ['任务图','P：对角处理；T：panel；U：更新；参数化依赖和就绪队列','既保证先后关系，又限制调度、图和线程开销。'],
 ['动态资源','Shape、packed容量、worker context、workspace lease','多矩阵缓存命中、释放和重新分配的总成本。'],
 ['VM证明','栈高、PC边界、循环步数、初始化、数组检查','证明仅免除相应检查；栈证书不等于数组安全或程序终止。'],
 ['观测协议','全矩阵文件、符号零、异常／partial清理、FP环境','优化成功路径时仍须守住错误顺序和只读 borrowed API。']], [74,184,WIDTH-258])
h('2.2 接口、评分和本地契约',2)
para('题面要求输入 C 源码、生成表示算子符号依赖的 Metadata，再由 Runtime 处理动态 N=3..10000 的 FP64 矩阵；Metadata 占15分、计算耗时占85分，文件 IO 不计入计算时间，真值完全一致是硬门槛。[1] 未公开评分映射与评测机器，因此不将秒数或 Metadata 字节换算官方分数。')
para('本地二进制协议采用小端 uint32：先 M，随后每矩阵 N 和行优先 N×N 个 double；输出相同结构。L 初始化全 +0，上三角全 +0。div(x,y)=x/y；madd(x,y,z) 为分别乘加；显式 fma 源变体另行识别。参考 C 独立编译，使用 -fno-fast-math -ffp-contract=off。这些缺省项是本地约定，不代表官网未公开内容。')
para('官网朴素图片转录的 C 是右看更新：先对角 sqrt，再列除法，再按既定次序更新剩余单元。普通稠密工作量约 N³/3；宽度 w 的带状数学部分约 O(Nw²)，但本题仍要求 dense 输入／输出，有限性检查和上三角清理为 O(N²)。因此不能用 N³/3 除以带状耗时包装成超高 GFLOP/s。')
h('2.3 计时与比较口径',2)
para('whole compute 包含检查、分配、图设置、调度、数学内核、导出及相关生命周期释放。kernel 是其中子项，不是评分总时间。metadata/read/write 单独记录；进程 wall 另含启动和加载，wall−compute 并不严格等于纯 IO。S33 的合并扫描只计入 input_validation_ms，structure_scan_ms 不重复计时；不同版本分项范围变化不计作提速。')

h('3 工程架构与数据回溯');h('3.1 从源码到执行',2)
para('Clang 前端解析实际源码和类型，展开支持的纯 helper，构建共享表达式和 PROGRAM；对完整 Cholesky 操作、地址、循环及更新顺序作匹配证明。Metadata 保留通用执行表示。Runtime 根据证明和调用条件选择原生 tiled、stage 或 VM；改步长、改算术或不满足快径证明的程序进入 VM，不借矩阵尺寸硬编码结果。')
table(['层次','当前机制','证据入口'],[
 ['源码前端','正常 AST／IR复用真实 Clang 版本；显式批处理冻结依赖；可 skip-ir','tools/analyze_source.py、tools/analyze_batch.py'],
 ['Metadata','schema2默认LF；共享表达式DAG＋紧凑指令；显式其他容器','docs/metadata.md；wire协议注册测试'],
 ['通用VM','decoded/threaded；显式不可变 PreparedVM session；栈／控制流认证','src/prepared_vm.cpp、threaded_vm.cpp；VM契约测试'],
 ['原生任务','参数化P/T/U DAG；heap ready；严格AVX2 separate mul/add','src/tiled_runtime.cpp、simd_kernel.cpp'],
 ['生命周期','owned输入复用、worker context、packed工作区、显式session/trim','src/native_workspace.cpp；input_buffer_ownership'],
 ['结构路径','整数位有限性＋带宽合并扫描；owned原地factor；完成后清upper＋swap','src/native_input_scan.hpp、banded_runtime.cpp']], [70,248,WIDTH-318])
h('3.2 默认与显式选项',2)
para('当前 CLI 默认 serial／1线程、VM计划 per-matrix、native workspace off。local preset 编译入显式 session／trim、PreparedVM 和认证能力，但“编译可用”并不表示默认启用。memory preset 关闭 prepared/threaded/proved operand stack 与 S33 合并扫描／结构输入复用；它不是非 x86 构建，也不是 ARM 验证。')
para('S33 的快径事实为调用内私有只读数据，绑定实际指针、N和带宽上限；外部 Metadata／Options 不可注入证书。扫描检查整个原始输入，包括上三角及提前发现 dense 后的尾部；±0均视为结构零，sNaN 用整数位检测，避免比较触发异常。只有真正拥有输入且 output 为空时才原地复用；borrowed 输入和已有输出保持原分配行为。')
para('原地结构因子计算保持既有逐单元数学顺序；当前 A(i,j) 在覆盖前读取，先前位置只作为 L 使用。数学成功后才清上三角并交换向量；swap 后不再访问旧 input.values。offband 的 ±0 不随意重写。工作区 trim 在结构证明之后按既有租约规则关闭，下一 dense 的重新分配费用仍计入 compute。')
para('浮点环境证据另有边界：classifier和静态proof要求包括INEXACT在内的全部异常位保持，并有独立严格测试；带计时的Runtime历史API对照仅排除既有chrono换算引入的FE_INEXACT／MXCSR precision差异，其余环境差异仍检查，原始差异记录保留。不能把primitive的全标志不变结论扩大为完整Runtime的全异常位不变；全文件真值门没有放宽。')
h('3.3 证据链与文件组织',2)
para('生产项目在 F 盘；全新构建、大输出和验证日志在 G:/Hackathon-stage2-artifacts/project19/20261014-exploration。本次冻结报告保存206源 SHA、实际编译／CTest 命令、两个 JUnit、八份源码流水线 JSON、完整48条 benchmark 样本和5条规模验证。原 C input/oracle 均先核对哈希并只读复用，未为每次优化重新计算昂贵参考。')
para('生产目录历史 object 和旧 test EXE 不作为本次证据。全新 local core 的9个 raw archive member、main及完整 PE payload 与 S33 相同，归档容器日期与 PE timestamp/checksum单独处理；没有按“所有不同字节都忽略”的方式假定相同。memory 配置因选项不同，保留其实际独立产物哈希。')

h('4 探索过程与完整测试');h('4.1 本次全量回归',2)
para('先冻结现有206源和生产 EXE／core，再从这份源码按两个真实 preset 全新 configure/build；每套 CTest 串行执行全部注册项。所有测试无失败、无跳过；未注册的 Python dispatch 单测另外运行。历史被否决的实验程序不属于当前可发布能力，未把运行它们当作当前测试要求。')
table(['配置','注册项','源码成功对照','预期拒绝','本次结论'],[
 ['local-mingw','15/15','188+49+63+105=405','24+17+12=53','全部通过'],
 ['memory-mingw','10/10','同上405','同上53','全部通过'],
 ['Python dispatch','3/3','策略／循环预算／load-pair单测','—','全部通过']], [87,59,151,102,WIDTH-399])
para('810次对照为完整 CLI 数据流比较，其中合计'+str(sum(x['matrix_executions'] for x in supp['pipelines']))+'次矩阵执行；批次内矩阵数不等于进程／测试数量。拒绝场景包括非法长度与 Shape、尾部数据、非有限／非 SPD、Metadata或步数限额、helper副作用、整数语义及不支持的精度／表达式；预期错误返回和输出保护均按各套报告检查。')
para('注册契约覆盖 Metadata wire、runtime 正确性、owned/borrowed、向量边界、VM预算、prepared/threaded／TOS2／栈证明和默认分派。local 新注册 classifier 测试在本次再次执行，覆盖独立整数位参考、只读／guard尾部和32种 FP 环境；它证明扫描 primitive，不单独证明所有运行时 fallback。此前 S33 的539次 API 语义门、配置门和大流集中门仍作为历史补充，未伪装成本次重复运行。')
para('为补齐未注册到CTest的已发布功能，本次另对每个preset执行完整380条结构源码集合，共760次全文件对照：四份独立C（scalar、转录page、blocked、显式fma），六种路由／ISA／队列配置，band宽度1/7/31/127/128/129、normal/subnormal/large/tiny，强制VM以及dense Toeplitz／low-rank的2047/2048/2049边界。另执行expanded／DAG／省略provenance／compact四种Metadata表示，三个源码、两引擎、两配置，共48次独立C对照。全部通过；未重跑旧候选性能比较或依赖过时AUTO几何断言。')
para('最小Metadata策略另外用六份源码核对schema2/3 × dag/table/expanded全部候选的展开图／PROGRAM／header等价与实际字节最小值，确认仅一次AST和一次IR编译；对每配置执行24次独立C全文件对照。两配置共48次成功、10项互斥CLI拒绝；实际preset的压缩容器编译门为OFF，两个压缩输入均按预期拒绝，原输出保留且partial不存在。没有把可选研究压缩构建冒称当前产品。')
para('因此本次独立源码流水线合计1666次成功流（810+760+48+48），预期拒绝118项（106+12）；另29条最大／混合流验证分开列示。该计数不将primitive classifier calls、CTest条目、内部VM契约次数或相同批次里的矩阵数重复相加。')
h('4.2 最大规模与多矩阵状态验证',2)
table(['新执行场景','配置／方式','矩阵序列','比较方式'],[
 ['行业对照中的原生24次','installed S33；1/4/16线程','dense4099、dense10000；band10000的1/16线程','每次全文件SHA等于冻结独立C真值'],
 ['混合Shape三次','S33 workspace off/session/session-trim；16线程','4096→10000→4096','逐块与3份原C记录全字节比较'],
 ['跨结构状态一次','S33 session-trim；16线程','dense4096→band10000→dense4096','逐块与原C记录全字节比较'],
 ['兼容最大dense一次','fresh memory preset；16线程','dense10000','800,000,008字节逐块完整比较']], [105,141,132,WIDTH-378])
para('5条额外规模验证全部通过，共13次矩阵执行；输出共 '+f"{sum(x['validation']['bytes'] for x in scale['cases']):,}"+' 字节。混合流只改 M 首部并拼接原始 N+payload 记录；参考同样逻辑拼接，未创建另一份1GB真值。最大 dense 和 band 的原 C 真值生成约504.67秒和481.61秒，是历史独立原 C 运行，本次仅复用并校验。')
para('本次测试未发现需要改动生产代码的缺陷。没有官方隐藏集、非Windows／ARM、完整跨编译器或所有数学病态矩阵的穷尽测试；数值库比对使用现有普通 dense 和 bandwidth7 对角占优样本，不足以声称所有条件数下的稳定性。')
h('4.3 逐阶段探索与采用理由',2)
para('S1-S33记录最近一轮阶段推进；它们之前的基础开发也构成当前系统。以下早期成果按能力路线回顾，数字来自冻结历史记录，不当作本次新执行计数。')
table(['早期阶段','探索形成的能力','关键取舍'],[
 ['端到端与源码变形','建立C→Metadata→Runtime→独立C真值链；动态Shape、二进制协议、错误／输出清理','先以完整输出锁住语义；自设分块、helper定义和官方转录源分别标注。'],
 ['类型与证明扩展','纯SSA helper、嵌套／prototype、整数语义、合法while与min边界；未证明变化回VM','覆盖增加与原生分派证明分开；不支持构造拒绝，整数未定义行为不当作C真值。'],
 ['任务／SIMD／布局','P/T/U块图、packed因子、AVX2、带状扫描、Shape边界；最大dense和band独立C缓存','AVX512和八行向量有负Shape；微内核或任务数理论不能代替whole性能。'],
 ['Metadata协议','共享DAG、table、schema3、最小文件策略；压缩完整容器为独立显式构建','保持图和PROGRAM完整；小noop固定开销反例；普通preset压缩仍OFF。'],
 ['VM演进','prepared decode、TOS2、GNU threaded、source-order与steps/PC合同','TOS2虽数值通过却所有配对负；threaded初期显式验证后才逐步进入默认。']], [89,242,WIDTH-331])
para('探索分为五条相互关联的路线：前端／Metadata、VM派发与认证、任务几何／调度、内存生命周期、结构化数据扫描。每条路线保留基准、候选与否决证据；显著整体收益后才做集中语义验收。附录列出全部33阶段及决策，而非只列成功项。')
table(['路线','主要成果','关键反例与限制'],[
 ['前端与Metadata','LF六源10724→10046 B；Clang3→2；显式批12→3','单次默认与显式批处理分别计时；不按70%批收益宣称所有分析更快。'],
 ['VM','threaded23流中位11.09%；紧凑记录；显式session＋栈／控制流认证','M>1自动session策略被否决；array证书、LOAD配对与多种编译开关未通过门。'],
 ['native微内核／任务','保留严格k链与AVX2；形状策略；小AUTO规避线程开销','6×8在未见Shape回退；row priority、k-unroll和多种tile不推广。'],
 ['生命周期','owned输入复用、首任务初始化、显式worker/session/trim','graph计时含因子分配；只优化导出子项未保证whole compute。'],
 ['结构识别','S33合并扫描＋真正owned原地复用','scan单项快42%–49%，但单独接入whole门失败；组合才达76%–82%。']], [88,180,WIDTH-268])
h('4.4 当前 S33 的完整配对结果',2)
para('S33相对上一产品固定11组、每组三对 AB/BA/AB、66个实际 CLI；无删除冷启动或负值。推广门为至少3/4主结构组 whole compute 中位下降≥10%，且每个控制组中位回退≤5%。四主组均通过，12/12对为正，峰值工作集约减49%–50%。该效果归于组合机制，不分摊为未经单因素实验支持的因果比例。')
table(['负载','compute成对中位降幅','wall成对中位降幅','工作集成对中位降幅'],[[r['case'].replace('-default-serial','').replace('-parallel16',' / t16'),f"{r['median_compute_reduction_percent']:+.2f}%",f"{r['median_wall_reduction_percent']:+.2f}%",f"{r['median_peak_working_set_reduction_percent']:+.2f}%"] for r in screen['summary']], [208,95,95,WIDTH-398])
para('dense6145/16线程的−4.11%、generic per-matrix／session的−2.30%／−1.28%均保留；故S33没有普通dense或通用VM加速结论。diagonal4096首对进程wall反而回退66.80%，也没有删去。带状N10000 compute约271→48ms、工作集约1531→768MiB来自该历史配对批，不把它冒称当前行业对照批的57ms。')

h('5 业界成果、benchmark与性能评价');h('5.1 检索范围与比较层级',2)
para('检索访问日期为2026-10-14。使用官方文档、维护者仓库、研究论文和作者／机构页面，覆盖 dense／band库、tile task runtime、编译IR、benchmark和可重复数值计算五类。引用[2]-[31]均提供可访问原始链接；没有把商业宣传、搜索摘要日期或仿真数字作为本机测量。')
table(['成果／benchmark','能参考什么','与本项目比较的边界'],[
 ['LAPACK DPOTRF/DPBTRF [2,3]','成熟blocked BLAS3与紧凑带状API','固定算子；band的KD由调用者给出；不承诺指定C顺序。'],
 ['OpenBLAS [4]','实际CPU库基线；本次直接调用work API','只测现有0.3.30构建；不是所有BLAS实现的排名。'],
 ['BLIS／Eigen [5–8]','microkernel、存储布局和固定分解基准','Eigen公开LLT例是float单线程；与本次FP64不可直接相比。'],
 ['PLASMA／PaRSEC／StarPU [10–13]','tile DAG、调度、数据放置、CPU/GPU异构','通用运行时成熟度更高；不默认保留每单元原C累加序。'],
 ['TaskBench [14]','调度依赖和最低有效任务粒度METG','合成计算／通信；不是Cholesky精度榜或通用100μs阈值。'],
 ['Cholesky-Bench 2026 [30]','统一BLAS层下OpenMP/HPX八种并行组织、tile sweep与no-op task overhead','128核EPYC双路、20次中位；不保证原始C位顺序；本次未执行。'],
 ['Eigen 2026 BLAS/LAPACK对照 [31]','FP32/FP64、POTRF等12算子；独占机器、绑核、10次重复','Xeon6444Y／Linux／AVX512单线程；不是本机成绩。'],
 ['PolyBench/C／Polly [15,16]','静态控制核与loop locality优化评测','包含Cholesky，但不覆盖本项目全部helper、VM和二进制失败协议。'],
 ['Polygeist／MLIR／DaCe [17–19]','更通用的C→IR、Affine分析与数据移动表示','本项目前端模式与证明范围明显较窄，不能据受限样本宣称编译能力相当。'],
 ['oneMKL CNR／ReproBLAS／ExBLAS [21–23]','自身计算可重复、准确／可重复累加','可重复不等于指定旧C计算顺序及符号零完全相同。'],
 ['MAGMA／cuSOLVER／SYCL研究 [25–27]','GPU、混合计算和batched因子分解','本次未做GPU测量；硬件、精度和数据传输条件不同。']], [141,161,WIDTH-302])
h('5.2 同机 OpenBLAS 对照实验设计',2)
para('主机为 AMD Ryzen 9 8945HX、16核32线程、约32GB内存，Windows x64；native为GNU15.2 Release，严格非fast-math／非隐式FMA。库为bundled NumPy2.3.5的OpenBLAS0.3.30 ILP64动态构建，实际报告core=SkylakeX、MAX_THREADS=24；每次显式设置并查询1/4/16线程池配置。查询值不证明所有线程持续活跃，也未强制库采用与native相同的AVX2 ISA。')
para('dense通过 scipy_LAPACKE_dpotrf_work64_ 直接就地计算；将行优先 lower 解释为列优先 upper，避免全矩阵转置／额外复制。band使用DPBTRF，按KD=7打包到8×N列优先AB，再还原dense输出。输入加载、数值比较不进计时；library wrapper含全有限性检查、pack/unpack和上三角+0清理，但不含真实band识别、Metadata／VM／task graph与原始错误协议。[2,3]')
para('8组各3对，顺序 native/BLAS、BLAS/native、native/BLAS，共48个全新进程，不预热、不删首轮。所有native全文件SHA等于独立C；所有库INFO=0。图表和主表分别保留whole native、kernel、pure library factor与wrapper。库峰值内存因数值比对保留C memmap，故不与native峰值RAM直接排名。')
para('这是共享宿主的探索性样本：无独占CPU、绑核或固定热状态。dense10000/t4第三个BLAS factor为7541.441ms，明显高于另外两次1822.511/1890.938；native/t16为5761.490/3338.070/2619.230ms。全部原值保留。三对中位可描述这一批趋势，不能充当稳健置信区间或硬件峰值。')
h('5.3 普通稠密与带状的实际结果',2)
table(['N／形状／线程','native whole / kernel ms','BLAS factor / wrapper ms','whole÷wrapper'],[[str(r['n'])+'/'+r['kind']+'/'+str(r['threads']),fmt(r['native_compute_ms'])+' / '+fmt(r['native_kernel_ms']),fmt(r['blas_factor_ms'])+' / '+fmt(r['blas_wrapper_ms']),f"{r['native_compute_over_blas_wrapper']:.3f}×"] for r in bench['summary']], [108,153,155,WIDTH-416])
bars([(f"dense10000/{r['threads']}线程 native",r['native_compute_ms']) for r in bench['summary'] if r['n']==10000 and r['kind']=='dense']+[(f"dense10000/{r['threads']}线程 BLAS包装",r['blas_wrapper_ms']) for r in bench['summary'] if r['n']==10000 and r['kind']=='dense'],'图1 同一批次N10000稠密中位时间（ms；越低越好）')
para('dense4099的whole native／library wrapper比为1.549、1.189、0.956；16线程小样本中native略快于这里的Python包装，但pure factor仍快于native kernel，不能据此说核心超越BLAS。dense10000三种线程预算均明显落后；native whole约30.01/98.77/99.86 GFLOP/s，pure library约58.28/176.28/222.52。GFLOP/s仅为N³/3的等效估计，不是硬件性能计数器结果。')
para('band7/N10000 native whole中位57.003／55.539ms，kernel1.882／1.939ms；library factor约0.490ms，而wrapper108.095／99.133ms。native扫描／owned生命周期集成在该wrapper比较中更快，library的紧凑带状数学内核更快。Python有限性与pack/unpack实现只是这一适配器的成本，不是OpenBLAS内建劣势或本项目普遍胜出；library还免去了真实宽度识别。')
h('5.4 精度、逐位一致与库可重复性',2)
table(['数据','库下三角位差数／位置数','相对因子Frobenius误差','结果判定'],[[r['case'],f"{r['blas_bit_mismatches_lower']:,} / {next(x['metrics']['lower_cells'] for x in bench['records'] if x['case']==r['case'] and x['variant']=='blas'):,}",f"{r['blas_relative_factor_error_to_C']:.3e}",'数学上接近；不满足全位真值'] for r in bench['summary']], [119,152,102,WIDTH-373])
para('上述误差为 ||L_library−L_C||F / ||L_C||F，比较因子本身；本次未独立测 ||A−LLᵀ|| 残差、条件数或跨全部SPD稳定性。dense差值约1.2e−16、最大绝对因子差值量级1e−14，却有约68%–70%的下三角位值变化；band42091个位差集中在79972个真实带内位置，不能让大量带外零稀释差异。native则完整头部、上三角、下三角和符号零均一致。')
para('LLVM把contract与reassoc分别定义为融合和重结合授权；没有授权时，代数等价本身不足以允许改变浮点表达式。[20] oneMKL CNR、cuSOLVER deterministic、ReproBLAS和ExBLAS的目标分别是限定条件下库结果可重复或可重复／准确累加。[21–23,26] 它们可提高确定性，却不能自动等同本题指定C位序列。2026年的BLAS准确性分级预印本讨论误差界和测试，不是原C逐位同义性；本项目未运行其分级套，也未获任何等级。[24]')
h('5.5 性能水平、核心差距与可达到的要求',2)
para('当前普通dense水平为“具备可审计语义、最大Shape与多线程能力的原型，但离成熟库吞吐仍有明显距离”。本机N10000在共享宿主下，native whole与此OpenBLAS pure factor相差约1.78–2.23倍；同时还承担严格顺序及额外运行时工作。这些限制解释了部分差距，却没有证明全部差距都不可避免，尤其并行扩展在本批4→16线程几乎停滞，值得独占环境下重新拆解。')
para('结构化方向的成熟度更高：实际owned原地路径显著降低whole compute和RAM，且dense协议下的O(N²)扫描／清理已主导时间。通用VM方向具有explicit session与栈证明，但仍受指令派发和可证明范围限制；不能把Cholesky快径成绩推广到任意C。前端和Metadata已有工程收益，但缺少同语义、同输出审计等级的外部解析器计时对照。')
table(['后续方向','提升空间与建议要求','可行性判断'],[
 ['稳定性能评测','独占／绑核、热状态记录、≥7对；保留冷／热两套；先复测4→16瓶颈','高：主要为评测工程；未改善代码也能更可靠判定差距。'],
 ['严格dense内核','优化packed布局、任务粒度、内存访问和同单元顺序保持的microkernel；whole收益≥5%且所有控制回退≤5%','中：有明显空间，但多条微调已失败；不承诺达到BLAS或固定倍数。'],
 ['结构路径／IO','把数学、扫描、清理、read/write分别优化；保持dense协议和所有±0／异常边界','中高：已有显著基础；band数学仅~2ms，优先优化~50ms外围与wall IO。'],
 ['更通用前端','扩大有证明的控制流／helper域；构建PolyBench与源码变形交叉集','中：可提高覆盖，证明与拒绝条件工作量大。'],
 ['VM额外认证','仅在immutable session中引入新的安全证书；以真实负载whole≥5%为门','中低：数组认证已有反例；证明更强不保证更快。'],
 ['放宽逐位／GPU分支','若另设误差／残差契约，可独立比较BLAS、MAGMA/cuSOLVER','条件性：需先改变问题要求；不作为当前严格契约的直接推广。']], [89,253,WIDTH-342])
para('TaskBench、PolyBench和各库benchmark宜作为补充维度，而非拼成一个跨硬件总榜：TaskBench测任务粒度，PolyBench测静态控制程序，Eigen公开示例是float，PaRSEC页面有历史分布式HPL，StarPU Task Graph Market有SimGrid重放数字。[8,11,13–16] 本报告没有执行这些外部套，故只比较模型和适用条件。')
para('Cholesky-Bench（2026）在双路EPYC7742、128工作线程、单线程BLAS上比较八种组织，20次FP64运行取中位；以BLAS no-op剥离任务成本，报告HPX约2μs／task、GCC OpenMP约7.6μs，async HPX在其最优tile时比OpenMP约快26%。[30] 可迁移的是固定数学层、tile sweep、空任务控制和去除多余barrier的方法；其库数学顺序与本题不同，百分比不能套到当前heap DAG。')
para('Eigen另有2026年9月公开的FP32/FP64库比较，与较早float分解页面不同：Xeon Gold6444Y、独占Linux节点、单线程AVX512／FMA、绑核且空出SMT sibling，12算子、874个operation-shape cells、每格10次至少0.2秒CPU计时并公开验证和原始CSV。[31] 它是改进本项目评测规范的直接范例；目前本机三对共享宿主采样的可信度更低，不能据图中跨机吞吐排名。')

h('6 团队使用指南与复现');h('6.1 构建与全量测试',2)
para('本次可直接复查全新G构建的JUnit和stdout，无需重算最大原C。若重新构建，应先configure再build，避免使用F目录旧cache或旧test EXE。按实际CMakePresets.json选项复现；原始全量测试脚本保存明确的Python／Clang／make路径。')
code('cmake --preset local-mingw -S <frozen-source> -B <G-build>\ncmake --build <G-build> -j3\nctest --test-dir <G-build> --output-on-failure\n# 兼容配置将preset改为memory-mingw，使用独立目录\npython -m unittest discover -s tests -p test_dispatch_profile.py -v')
para('run_full_tests.py只允许新空批次，避免覆盖既有记录；修改工作根路径或复制脚本到新的日期目录后重跑。补充桥接脚本 run_supplement.py 解析真实 archive payload 并核对PE；run_scale_tests.py按只读参考逻辑拼接比较。脚本不重新生成最大C oracle。')
h('6.2 Runtime与benchmark',2)
code('cholesky_runtime --metadata program.meta --input matrices.bin\n  --output result.bin --scheduler parallel --threads 16\n# 原生命令参数示意；实际命令列表以JSON records为准\n# workspace显式选项：--native-workspace session 或 session-trim\n# VM显式选项：--vm-plan session；默认per-matrix')
para('run_industry_benchmark.py与openblas_case.py记录库DLL哈希、真实config/core、每次配置线程数与timer；没有调用np.linalg.cholesky包住整段计时。必须保持ILP64接口、列／行布局与UPLO解释。若换库版本／线程预算／CPU，创建新批次，并保留原批次所有样本；不得用新最快值覆盖旧中位。')
para('全部原C参考具有独立源码／输入／输出哈希。更换helper、源码、编译器浮点选项或输入生成法后，旧oracle只能在确证同一契约时使用。显式FMA真值与普通madd真值分开；解析4I参考、原C参考、派生主子矩阵和已验收FMA baseline均分别标明，不能笼统称官方C。')
h('6.3 验收、回滚与报告维护',2)
para('任何下一优化先冻结候选与基准，针对真正受影响路径做组件／whole筛选，达到预先门槛后集中验收，再做源／core／EXE一致性桥接。需记录全部负样本、失败清理、borrowed/owned以及FP环境边界；没有单项收益时停止扩大该方向。生产回滚路径和收据位于S33 installed-runtime.json，本轮未更换生产二进制。')
para('报告PDF由build_report.py生成，report-content.json保存实际段落和表格源， evidence-index.json/zip保存可审计的轻量证据。大矩阵二进制保留原位置，仅附路径、长度和SHA；数据包不重复装入数十GB测试输出。报告沿用参考PDF的A4、封面／目录、蓝色分层标题、正文比较和原始数据附录组织，内容完全按本题重新编写。')

h('7 原始数据、验证与参考附录');h('7.1 本次注册测试清单',2)
rows=[]
for x in full['profiles']:
 for name in x['registered_tests']:rows.append([x['profile'],name,'PASS'])
table(['实际preset','注册测试名称','结果'],rows,[95,WIDTH-150,55])
h('7.2 四类源码流水线逐配置结果',2)
table(['配置／报告','成功流','矩阵执行','拒绝','报告SHA256前16位'],[[('local' if 'local-mingw' in x['path'] else 'memory')+'/'+Path(x['path']).name,str(x['strict_success_runs']),str(x['matrix_executions']),str(x['rejections']),x['sha256'][:16]] for x in supp['pipelines']],[182,48,63,40,WIDTH-333])
para('上述成功流含该流水线单独的性能／符号零／重复并行控制，只统计报告中确有byte_identical=true的记录，不按计划数猜测。四类各配置405条，不把CTest条目数与内部比较数相加。','small')
table(['新增集合','local成功流','memory成功流','独立真值'],[['完整结构源码集合',str(structured['counts']['local']),str(structured['counts']['memory']),'四份独立C；全文件字节'],['Metadata四种表示',str(sum(x['profile']=='local' for x in structured['metadata_modes'])),str(sum(x['profile']=='memory' for x in structured['metadata_modes'])),'三份独立C；VM与tiled']], [175,88,88,WIDTH-351])
table(['最小编码配置','成功流','CLI互斥拒绝','压缩输入拒绝'],[[x['profile'],str(x['success_runs']),str(x['conflicting_options_rejected']),'1'] for x in encoding['profiles']], [175,88,88,WIDTH-351])
h('7.3 同机行业对照全部原始样本',2)
table(['组／pair／变体','factor或compute ms','wrapper或kernel ms','wall s','位差／native真值'],[[r['case']+'/p'+str(r['pair'])+'/'+r['variant'],fmt(r['metrics']['compute_ms'] if r['variant']=='native' else r['metrics']['factor_ms']),fmt(r['metrics']['kernel_ms'] if r['variant']=='native' else r['metrics']['wrapper_ms']),f"{r['wall_seconds']:.3f}",'全文件一致' if r['variant']=='native' else str(r['metrics']['bit_mismatches_lower'])] for r in bench['records']],[170,84,88,52,WIDTH-394])
para('native列分别为whole compute／kernel；BLAS列分别为pure factor／wrapper。这48个原值没有去除异常点；wall未用于库数学排名。每次命令、资源采样及全量字段位于industry-benchmark/report.json。','small')
h('7.4 当前 S33 配对原值与负项',2)
table(['负载','compute三对降幅%','wall三对降幅%'],[[r['case'],', '.join(f'{v:+.2f}' for v in r['paired_compute_reduction_percent']),', '.join(f'{v:+.2f}' for v in r['paired_wall_reduction_percent'])] for r in screen['summary']],[222,135,WIDTH-357])
h('7.5 33阶段决策台账',2)
cn={
'S1':'threaded VM默认','S2':'Metadata默认LF','S3':'6×8微内核候选','S4':'Clang版本复用','S5':'显式批处理／skip-ir','S6':'流级worker context','S7':'生命周期分项／输入复用','S8':'LOAD+LOAD组合','S9':'PreparedVM显式session','S10':'小AUTO串行stage','S11':'安装组合直接性能','S12':'显式factor容量缓存','S13':'紧凑decoded指令','S14':'最终Shape／最大规模','S15':'结构路径session-trim','S16':'自动M>1 session','S17':'U后继直接认领','S18':'finite扫描展开','S19':'byte初始化标记','S20':'单次scalar frame分配','S21':'原子／mutex发布计划','S22':'栈／控制流认证','S23':'独立数组索引证书','S24':'导出合并upper清零','S25':'row-first ready优先级','S26':'threaded -fno-gcse','S27':'goto duplication64','S28':'threaded -fno-crossjumping','S29':'k-pair展开静态检查','S30':'k-pair调度barrier','S31':'合并finite/band组件','S32':'合并扫描单独接入CLI','S33':'合并扫描＋owned结构复用'}
accepted={'S1','S2','S4','S5','S6','S7','S9','S10','S12','S13','S14','S15','S22','S33'}
decisions={'S3':'新Shape回退，未推广','S11':'测量；非新改动','S27':'对象未变，不执行性能','S29':'spill风险；仅静态','S31':'仅组件门通过','S23':'三种数组认证筛选均失败'}
table(['阶段','探索内容','最终决策','证据定位'],[[x['id'],cn.get(x['id'],x['name']),'已接入／显式能力' if x['id'] in accepted else decisions.get(x['id'],'whole／护栏门未过；未接入'),str(x.get('evidence',x.get('composition_gate','详见阶段JSON'))).split('project19')[-1]] for x in stages['stages']],[36,154,133,WIDTH-323])
para('每行是该阶段的最终结论；历史文档中的“未安装”等时间态以最终台账及S33安装收据为准。各阶段独立收益不累乘。详细源hash、样本、回滚和验收链接保留在project19-stage-metrics-2026-10-13.json。','small')
h('7.6 完整版本与关键数据哈希',2)
hashrows=[['生产CLI',full['installed_runtime']['sha256']],['生产core',full['installed_core']['sha256']],['原C转录源','0363f60d7f848b33c4e42a2be0d15d8d8d89c87caeae6b103f6a3d2059fd3a39'],['OpenBLAS DLL',next(r['metrics']['dll_sha256'] for r in bench['records'] if r['variant']=='blas')],['混合4096/10000/4096输入',scale['mixed_input_sha256']],['dense-band-dense派生输入',scale['trim_input_sha256']]]
for c in bench['plan']['inputs']:hashrows.extend([[c['label']+' input',c['input_sha256']],[c['label']+' C oracle',c['oracle_sha256']]])
table(['对象','完整SHA256'],hashrows,[130,WIDTH-130])
para('大input／oracle路径见industry-benchmark/report.json的plan.inputs；补充流记录源段路径。evidence-index.json给出所有本次轻量报告／脚本／JUnit／日志的路径、字节数和完整SHA。全206个源hash位于full-test/report.json，未在正文逐项重复。','small')
h('7.7 一手来源与benchmark目录',2)
refs=[
('赛题页面与本地要求记录','https://www.chaspark.com/#/races/competitions/1326691788365586432','题面及缺省项边界；本地docs/requirements.md记录2026-10-10核查。'),
('LAPACK DPOTRF官方文档','https://www.netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html','dense blocked Level3 BLAS接口、UPLO与INFO。'),
('LAPACK DPBTRF原始实现／接口文档','https://www.netlib.org/lapack/double/dpbtrf.f','带状AB布局和KD；该页面为历史LAPACK3.2源。'),
('OpenBLAS维护者仓库','https://github.com/OpenMathLib/OpenBLAS','CPU优化BLAS实现；本次实际运行0.3.30 DLL。'),
('BLIS FAQ','https://github.com/flame/blis/blob/master/docs/FAQ.md','框架与microkernel职责。'),
('BLIS Performance','https://github.com/flame/blis/blob/master/docs/Performance.md','Level3比较环境；不直接等同Cholesky成绩。'),
('Eigen LLT官方文档','https://eigen.tuxfamily.org/dox/classEigen_1_1LLT.html','就地分解、三角布局、SPD条件。'),
('Eigen Dense Decomposition Benchmark','https://libeigen.gitlab.io/eigen/docs-master/group__DenseDecompositionBenchmark.html','i7@2.6GHz、clang AVX/FMA、float单线程；LLT4000为374.55ms，不能直接与本报告FP64相比。'),
('Gustavson等：Level-3 Cholesky Factorization Routines, 2011','https://www.netlib.org/lapack/lawnspdf/lawn249.pdf','LAWN249；register blocking和packed表示。发布日期June11,2011，非搜索引擎抓取日期。'),
('PLASMA官方论文目录','https://icl.utk.edu/plasma/pubs/index.html','CPU多核tile算法；2019 OpenMP版本ACM TOMS45(2)。'),
('PaRSEC项目与性能概述','https://icl.utk.edu/parsec/overview/','参数化DAG、多核／分布式；历史Griffon HPL是LU benchmark，不能称Cholesky同机数据。'),
('StarPU官方Features','https://starpu.gitlabpages.inria.fr/features.html','依赖／data管理、performancemodel及CPU/GPU。'),
('StarPU Task Graph Market','https://starpu.gitlabpages.inria.fr/market.html','SimGrid任务重放；页面显示的GFLOP/s不是本机真实执行。'),
('Slaughter等：Task Bench, SC2020','https://arxiv.org/abs/1908.05790','15个runtime、Cori最多256节点、METG；另见github.com/StanfordLegion/task-bench。'),
('PolyBench/C维护仓库','https://github.com/ferrandi/PolyBenchC','30个static-control kernel；参数／计时／cacheflush及Cholesky。'),
('Polly Performance','https://polly.llvm.org/performance.html','公开页面测量为2011 LLVM/Clang、XeonX5670；不当作2026最新性能。'),
('Polygeist维护仓库／PACT2021','https://github.com/llvm/polygeist','C/C++→MLIR；Moses/Chelini/Zhao/Zinenko。'),
('MLIR Affine Dialect','https://mlir.llvm.org/docs/Dialects/Affine/','维度／symbol、整数affine控制和依赖分析。'),
('Ben-Nun等：Stateful Dataflow Multigraphs, SC2019','https://arxiv.org/abs/1902.10345','DaCe/SDFG，程序与data movement优化分离。'),
('LLVM Language Reference','https://llvm.org/docs/LangRef.html','contract与reassoc授权语义及浮点变换界限。'),
('Intel oneMKL CNR Control','https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2024-2/conditional-numerical-reproducibility-control.html','固定条件下的库可重复性；不保证指定原C顺序。'),
('Berkeley ReproBLAS','https://bebop.cs.berkeley.edu/reproblas/','binned可重复累加。'),
('ExBLAS项目仓库','https://github.com/riakymch/exblas','准确／可重复BLAS扩展。'),
('Demmel等：How to grade the accuracy of BLAS, 2026','https://arxiv.org/abs/2609.12307','2026-09-11预印本，误差界与测试等级；本项目未执行该grading。'),
('MAGMA POTRF官方文档','https://icl.utk.edu/projectsfiles/magma/doxygen/group__magma__potrf.html','GPU／hybrid／batched及workspace；本报告无GPU实测。'),
('NVIDIA cuSOLVER官方文档','https://docs.nvidia.com/cuda/cusolver/index.html','deterministic mode受硬件／软件条件限定；不自动等于C参考。'),
('Thüring/Strack/Pflüger：SYCL heterogeneous solvers, IWOCL2026','https://arxiv.org/abs/2605.13209','论文摘要报告large Cholesky异构CPU+GPU最高29%优于其GPU-only；不是本机或本题性能。'),
('PaRSEC项目首页','https://icl.utk.edu/parsec/','模块化runtime、参数化任务表示和workstealing。'),
('StarPU Quick Guide','https://starpu.gitlabpages.inria.fr/quickGuide.html','校准performance model与任务执行配置。'),
('Strack/Van Craen/Pflüger：Cholesky-Bench, 2026','https://arxiv.org/html/2606.11937v1','2026-06-10；双路128核Zen2，OpenMP／HPX八种组织，20次FP64中位；BLAS no-op overhead控制。'),
('Eigen vs BLAS/LAPACK：Xeon Gold6444Y, September2026','https://libeigen.gitlab.io/benchmarks/2026-09-xeon-gold-6444y-blas-lapack-avx512/','FP32/FP64单线程POTRF等12算子，独占绑核，10次重复，验证及raw CSV可查。')]
for i,(title,url,note) in enumerate(refs,1):
 para(f'[{i}] <b>{esc(title)}</b><br/><a href="{esc(url)}" color="#2e6489">{esc(url)}</a><br/>{esc(note)}','small')
para('除题面已有核查记录外，以上来源于2026-10-14联网读取／检索。文献分为实际同机库基线、公开异机benchmark、仅方法参考；公开数据从未混入48条本机样本。搜索原始返回保留在research-raw-results.json，内部检索编号不作为对外引用。','small')

data=dict(title='第19题完整探索报告',version='S33',date='2026-10-14',blocks=content,references=[dict(id=i+1,title=x[0],url=x[1],note=x[2]) for i,x in enumerate(refs)],evidence=dict(full_tests=str(ROOT/'full-test/report.json'),supplement=str(ROOT/'full-test/supplement.json'),structured=str(ROOT/'structured-test/report.json'),encoding=str(ROOT/'encoding-test/report.json'),benchmark=str(ROOT/'industry-benchmark/report.json'),scale=str(ROOT/'scale-test/report.json')))
(ROOT/'report-content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
dest=OUT/'project19-exploration-2026-10-14.pdf'
doc=Report(str(dest),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=48,bottomMargin=47,title='第19题完整探索报告：全量测试与业界对照',author='Project19 Exploration',pageCompression=1)
doc.multiBuild(story,onFirstPage=footer,onLaterPages=footer)
print(json.dumps(dict(pdf=str(dest),bytes=dest.stat().st_size,blocks=len(content),references=len(refs)),ensure_ascii=False))
