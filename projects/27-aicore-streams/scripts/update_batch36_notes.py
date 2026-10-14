"""Append the verified resumed milestone without rewriting R31 history."""
from pathlib import Path
note='''

第36批续研默认（R31历史冻结保持不变）：单消费者/共享输出消费者对的有界贪心闭包宏，仅在旧方法未找到可行计划时启用。输出分配、原始直接消费者释放及 Event 规则保持原图，提交仍只依赖 problem.h 和标准库。源 SHA-256 `6b913bef5a17fc0c7d8a9db9889f443e9d2995d44909087a976b9061bed86032`，默认二进制 `6c9ce18bab1ba049c9087eb7eda200516dd24f7c806d9c86e6cb34aa715b02d8` 冻结于 `research/batch36/`。

1193 记录中 1128 按预期通过（含1个预期不可行控制），65 条有独立 witness 仍未解；202 困难三轮配对均133→137合法，4恢复、0丢失、共同133例 T/peak不变、0模型分歧。979严格回归49.395秒、144最优标尺/33证书、CTest5/5 1.45秒、提交独立无警告编译通过。新640项子集DP/独立Event/预算检查、99781个持出下界检查与96个外部CP-SAT小图决定通过；13个困难图CP-SAT短预算均UNKNOWN，R32/R33无恢复而未推广。

三轮202全调用墙时中位24.110155→25.001174秒、线程CPU21.171875→23.234375秒（+9.74%），全CLI25.944064→26.564670秒；成本包括失败搜索，不能声称整体加速。共同65持续失败wall14.803591→16.144965秒、CPU12.984375→15.000000秒。CLI峰值工作集约302.1MiB，含JSON/witness/独立验证，不等于solver额外内存。证据见 `reports/paired-hard-batch36-summary.json`、`reports/final-hard-batch36.json`、`research/batch36/provenance.json`。新续研报告为 `reports/project27-research-resumed.tex`，旧R31报告不覆盖；官方测试包、隐藏分数与真实NPU仍未取得。继续研究分支隔离保存，未验证改善不推广默认。
'''
for p in ['README.md','docs/TEST_READINESS.md']:
    file=Path(p);s=file.read_text(encoding='utf-8')
    assert '第36批续研默认' not in s
    file.write_text(s+note,encoding='utf-8')
print('Updated README and test readiness with frozen batch36 evidence')
