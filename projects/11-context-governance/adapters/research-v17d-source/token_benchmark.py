"""Exactly 128K real model tokens: importance analysis only, not model inference."""
import argparse
import json
import math
from pathlib import Path
import statistics

from .core import Item, analyze_importance, render
from .local_model import ModelTokenCounter


def workload(counter, count, target=131072, profile='repeated'):
    items=[]
    for i in range(count):
        if profile=='repeated': text=f'parser source_{i} trace 中文' + ' x'*(target//count-20)
        else:
            source=''.join(f'def parse_{i}_{j}(value_{j}):\n    if value_{j} < {j}:\n        raise ValueError("中文错误日志 parser trace {i}-{j}")\n    return value_{j} * {j+7}\n' for j in range(max(80,target//count//10)))
            ids=counter.tokenizer.encode(source,add_special_tokens=False)
            text=counter.tokenizer.decode(ids[:target//count-20])
        items.append(Item(f'item-{i}','memory',text,False,(i%7)/7))
    for _ in range(10):
        actual = counter.count(render(items))
        if actual==target: return items
        last=items[-1]; delta=target-actual
        text=last.text+' x'*delta if delta>0 else counter.tokenizer.decode(counter.tokenizer.encode(last.text,add_special_tokens=False)[:delta])
        items[-1]=Item(last.id,last.kind,text,last.protected,last.utility)
    raise RuntimeError('failed to construct exact token count')


def main():
    from transformers import AutoTokenizer
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--repeats',type=int,default=30)
    parser.add_argument('--output',default='artifacts/128k-token-importance.json')
    args=parser.parse_args()
    tokenizer=AutoTokenizer.from_pretrained(args.model,local_files_only=True,trust_remote_code=False)
    counter=ModelTokenCounter(tokenizer)
    report={'origin':'self-created real-token importance microbenchmark', 'tokens':131072,
            'counter':counter.name, 'includes':['relevance token extraction','history utility','exact duplicate novelty'],
            'excludes':['tokenizer load','input tokenization','context assembly','model inference','quality evaluation'], 'cases':[]}
    for profile in ['repeated','diverse-code-chinese-errors']:
      for count in [16,64,256]:
        items=workload(counter,count,profile=profile)
        for _ in range(3): analyze_importance('parser trace 中文',items)
        timings=[analyze_importance('parser trace 中文',items)[1] for _ in range(args.repeats)]
        report['cases'].append({'profile':profile,'item_count':count,'actual_input_tokens':counter.count(render(items)),
            'p50_ms':statistics.median(timings), 'p95_ms':sorted(timings)[math.ceil(.95*len(timings))-1],
            'max_ms':max(timings),'all_samples_under_100ms':max(timings)<100,'samples_ms':timings})
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
