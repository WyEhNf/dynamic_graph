"""Independent valid bigint Event controls, exact 160-case reproduction."""
import importlib.util,json,random
from pathlib import Path
sp=importlib.util.spec_from_file_location('big','scripts/make_numeric_parallel_batch42.py');mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
rng=random.Random(202610114201);M=mod.M;cases=[]
for seed in range(160):
 n=rng.randrange(3,8);ids=rng.sample(range(10,1000),n);owners=[rng.randrange(4) for _ in ids];nodes=[]
 for i in range(n):nodes.append(dict(id=ids[i],core_type=rng.choice(['AIC','AIV']),core_num=rng.randrange(1,9),exec_time=rng.randrange(1,100),workspace_memory=rng.randrange(5)*(M//32),output_memory=rng.randrange(3)*(M//64),inputs=[ids[j] for j in range(i) if rng.random()<0.3]))
 flows=[dict(tasks=[]) for _ in range(4)];before=[set() for _ in ids];recorders=set()
 for i,v in enumerate(nodes):
  for p in v['inputs']:
   j=ids.index(p)
   if owners[j]!=owners[i]:recorders.add(j);before[i].add(j)
 for i,v in enumerate(nodes):flows[owners[i]]['tasks'].append(dict(op_id=v['id'],wait_before=[13+j*37 for j in sorted(before[i])],record_after=13+i*37 if i in recorders else -1))
 h=dict(aic_core_num=8,aiv_core_num=8,stream_num=4,memory_limit=M,event_record_time=rng.randrange(5),event_wait_time=rng.randrange(5));plan=dict(streams=flows);valid,T,peak=mod.simulate(h,nodes,plan);assert valid
 rng.shuffle(nodes);cases.append(dict(name=f'bigint_parallel_valid_seed202610114201_{seed}',hardware=h,nodes=nodes,deadline_us=M,fixed_plan=plan,gold_valid=True,gold_T=str(T),gold_peak=str(peak)))
Path('data/numeric-parallel-valid-batch42.json').write_text(json.dumps(dict(format='aicore-local-v1',cases=cases)),encoding='utf-8')
print(len(cases),'independent bigint heterogeneous-contention valid controls')
