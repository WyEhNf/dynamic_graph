"""Render the final status from frozen verification, preserving historical batches."""
import hashlib
import json
from pathlib import Path


def main():
    v=json.loads(Path('docs/validation.json').read_text(encoding='utf-8'));b=v['resource_clique_batch31']
    assert b['source_sha256']==hashlib.sha256(Path('solution/solution.cpp').read_bytes()).hexdigest()
    status=f"""
第三十一批最终默认冻结 `research/batch31`：源 SHA-256 `{b['source_sha256']}`，benchmark 二进制 `{b['exe_sha256']}`。
1193 条记录中 1124 按预期通过，69 条有独立可行 witness 但当前启发式未解。记录含共享官方样例、参数控制及一条预期不可行压力输入，不是 1124 个独立可行拓扑。
979 严格回归 {b['regression']['elapsed_wall_seconds']:.3f} 秒；144 独立最优标尺审计、33 份双界证书；CTest 4/4 1.01 秒，单文件 GCC -O2 -Wall -Wextra -Wpedantic 编译无警告。
新界使用单个核池的请求严格超过半容量，以及 Compute 整段同时存活的 workspace+output 严格超过显存半容量的互斥时长和；不同核池不合并。除2比较避免乘2溢出，正数64位饱和加法，恰好半容量负控制保留。
12 新解析控制 T/peak 全部最优；三轮配对调用墙时 445.003→88.126ms、线程 CPU 453.125→78.125ms。143 通用持出 T/peak 保持但线程 CPU +9.3%，12 混合硬件仍 5/12 且全失败路径线程 CPU +1.0%；专项收益不外推为通用加速。
最终202困难记录133合法可行/69未解，与冻结30状态/T/peak保持；失败调用墙时19.334秒、线程CPU18.250秒。所选1193记录一次最终功能核对的总调用墙时70.879秒、线程CPU64.094秒，非同期单次功能证据，不是配对性能结论。完整证据见 `reports/final-hard-batch31.json` 与 `docs/validation.json`。
单文件提交仅problem.h+标准库，保留原直接消费者输出释放；JSON本地adapter不冒充官方.case。当前没有官方包/隐藏得分/真实NPU或平台CPU/RAM时限。后续一名熟悉C++开发者预估12–21工作日、72–126有效小时，覆盖一般beam、选择性Event、预算、oracle、流式测试及未来官方适配；算法收益仍需新witness和成本验证。
"""
    for file in ['README.md','docs/TEST_READINESS.md','solution/README.md','DEVELOPMENT_PLAN.md']:
        p=Path(file);text=p.read_text(encoding='utf-8')
        if file=='README.md':
            lines=text.splitlines();lines[4:4]=['最终状态：1193条案例记录1124按预期通过、69条有witness仍未解；144份独立最优标尺、CTest4/4及单文件编译通过。默认R31源 `'+b['source_sha256']+'`。以下按批数字为冻结历史，最终完整证据见 [验证记录](docs/validation.json) 与 [研究报告](reports/project27-research.tex)。','']
            text='\n'.join(lines)+'\n'
            text=text.replace('已实际运行：CTest 3/3通过；72项调度语义检查、265项内部模型/JSON/变换性质检查、81案快速批量测试；','已实际运行：CTest 4/4通过；72项调度语义检查、269项内部模型/JSON/变换性质检查、288项冻结递推及24项排序/环/alias检查、3项宽投影与6项资源解析检查、81案快速批量测试；')
            stale='下一批针对密集输入分流进行等价代数优化（按父所属Stream汇总），预计将重复扫描O(S*m)降到O(m+n*S)。用冻结逐父递推对照、输出计划逐条相同检查及新密集/跨层有解图三次配对验证后再决定保留。新测试不改判题接口，不把宿主CLI成本混入逻辑deadline。'
            text=text.replace(stale,'第22批已实现密集输入分流等价代数优化并保存冻结对照；后续资源互斥界与完整最终结果见文末及研究报告。')
        p.write_text(text+'\n\n'+status,encoding='utf-8')
    print('updated final status in four project documents')


if __name__=='__main__':main()
