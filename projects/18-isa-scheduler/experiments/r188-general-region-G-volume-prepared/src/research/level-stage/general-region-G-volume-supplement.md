# R188：原R186 immutable实验的G盘资源补充（静态，未执行）

保留R186全部原件。新launcher `scripts/research_general_region_full336_g.py` 只改变输出volume与冻结资源配置，不改变core/wrapper/selector/预算/输入/initial/完整验证/增量标签重放。仍原336，272合法initial总192902COPY，64原47/9/8状态，108zero与164通用搜索；全336平均null，不删除困难图。

## 真实owned输出volume

全部大型 complete JSONL gzip、所有immutable/OPEN/unfinished frontier gzip、每input best gzip：

`G:\Hackathon-stage2-artifacts\project18\r187-general-region-full336`

小报告、source/evidence manifest、baseline-check索引、partial/checkpoint：

`F:\Hackathon\projects\18-isa-scheduler\experiments\r187-general-region-full336`

两目标必须不存在，实际run均mkdir(exist_ok=False)，不覆盖。2026-10-12T04:58:00.9986510Z实际PowerShell核：G目标不存在，parent真实解析`G:\Hackathon-stage2-artifacts\project18`，唯一GUID探针CreateNew写1B并Flush(true)成功，随后仅删除自己这一临时文件。Gfree515572948992B，Gused21297958912B。没有junction、目录迁移或删旧证据，没有读取/修改用户其他应用。

runtime resource_snapshot明确从**实际G volume**shutil.disk_usage读取disk_free，RSS保留本进程实际current/lifetime peak，RAM实时GlobalMemoryStatusEx。F盘只另列small_report_free并用64MiB最小空间守卫，不能用F默认512MiB reserve让G有资源的图人为停止。core显式接收G snapshot，不触发默认F disk getter；500ms包含snapshot时间。

## 全部证据与资源halt

G至少512MiB reserve +每input actualF/N/W包络；R186最大package145511284B、单proposal8251834B，累计未压缩最坏175973778432B（约164GiB）。G实际约480GiB余量覆盖静态累计包络，但不保证其他用户应用不写盘；不预设gzip压缩率。不采样/漏标签，不删除旧文件。

complete sink实际G编码/flush后再检查实际free；当前已生成所有diagnostic逐条完整写G并验证，完成后才决定未来tail resource_unknown。完整candidate与best保持initial fallback。G文件路径在小report/index为**绝对路径**，source/evidence manifest同样给absolute G SHA；frontier压缩和decoded SHA双列，根可直接独立读取。OSError保留已经写出的G/F证据，failure尽量写F，不自动重启或迁移。

当前仅 `--prepare`；80小图/hand11/336 solver、raw oracle、tests均不运行。预审后唯一命令：`.\.venv\Scripts\python.exe scripts\research_general_region_full336_g.py --run`。新source freeze R188、依赖R186 manifest SHA与原输入/initial SHA，任何变化fail closed。所有原R186及此前实验不修改。
