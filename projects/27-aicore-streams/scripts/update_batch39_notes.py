"""Use frozen evidence for docs; retain all prior milestone paragraphs."""
import json
from pathlib import Path
f=json.loads(Path('research/batch39/provenance.json').read_text(encoding='utf-8'))
h=json.loads(Path(f['paired_hard']).read_text(encoding='utf-8'));n=json.loads(Path(f['paired_new']).read_text(encoding='utf-8'))
note=f'''

第39批续研默认：保留R36消费者宏，再加宏内安全提前消费、严格嵌套fork/join连续子块profile候选；结构识别先于失败前沿搜索。源SHA-256 `{f['source_sha256']}`、默认二进制 `{f['default_exe_sha256']}` 冻结于 `research/batch39/`。没有修改原始依赖/Event/直接消费者释放，不宣称dominant profile或任意交叠全局最优。结构边界检查线性，order递归拼接最坏O(n·depth)，depth≤512/n≤4096；一般前沿仍≤768、每调用8M搜索工作上限（不是CPU时限）。

原202困难三轮137→139合法、63有witness未解；共同137 T/peak不变，新增70与766节点两例。新增36随机分叉/权重/seed图（4–1534节点）三轮14→36合法，共同14 T/peak保持，22恢复。新witness来自96独立随机DFS、真实原边释放核验，没有使用候选递推。12小图全子集最小peak与连续子块穷举、36结构正例/3外部边界负例、1120前沿DP/Event/预算检查通过。累计1229记录1166按预期通过，含1不可行预期控制；旧1193中1130通过，不将参数记录夸成独立拓扑。979严格回归、144最优标尺/33证书、CTest5/5 0.99秒及单文件无警告编译通过。

原202全求解wall中位{h['median_all_solve_us_before']/1e6:.6f}→{h['median_all_solve_us_after']/1e6:.6f}秒，threadCPU {h['median_all_thread_cpu_us_before']/1e6:.6f}→{h['median_all_thread_cpu_us_after']/1e6:.6f}秒（+3.14%），全CLI {h['median_wall_seconds_before']:.6f}→{h['median_wall_seconds_after']:.6f}秒，包含全部失败成本。新结构36全求解wall {n['median_all_solve_us_before']/1e6:.6f}→{n['median_all_solve_us_after']/1e6:.6f}秒、CPU {n['median_all_thread_cpu_us_before']/1e6:.6f}→{n['median_all_thread_cpu_us_after']/1e6:.6f}秒（-11.30%），CLI {n['median_wall_seconds_before']:.6f}→{n['median_wall_seconds_after']:.6f}秒；结构族少走无效搜索的收益不能外推通用图。完整失败分母与搜索成本见 `reports/final-hard-batch39.json`，三轮原始记录见 `reports/paired-hard-batch39-summary.json`、`reports/paired-forkjoin-batch39-summary.json`。旧R31/R36证据不覆盖，新续研TeX单独保存，下一隔离分支未验证不混入默认结论。
'''
for p in ['README.md','docs/TEST_READINESS.md']:
    file=Path(p);s=file.read_text(encoding='utf-8');assert '第39批续研默认' not in s
    file.write_text(s+note,encoding='utf-8')
print('Updated batch39 docs from frozen evidence')
