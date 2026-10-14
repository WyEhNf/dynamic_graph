"""Explicit thinking-budget control followed by an EOS-checked code completion.

The inserted closing tag is a decoding control, not a model-generated reasoning
conclusion. Every generated token and both input passes count toward the cost.
"""
from time import perf_counter
from .candidate_gate import final_answer


def generate_bounded_reasoning(generate, tokenizer, prompt, *, reasoning_budget=1024,
                               answer_budget=1536, sampling=None, seed=None, max_seconds=240):
    if type(reasoning_budget) is not int or reasoning_budget < 1:
        raise ValueError('reasoning_budget must be a positive integer')
    if type(answer_budget) is not int or answer_budget < 1:
        raise ValueError('answer_budget must be a positive integer')
    started=perf_counter()
    first=generate(prompt,reasoning_budget,thinking=True,sampling=sampling,seed=seed,max_seconds=max_seconds)
    if first.get('stopped_on_eos'):
        return {**first,'segments':[first],'forced_reasoning_end':False,
                'reasoning_budget':reasoning_budget,'answer_budget':answer_budget}
    raw=first['output']
    closings=raw.count('</think>')
    if closings>1 or raw.count('<think>')>1:
        return {**first,'segments':[first],'protocol_error':'malformed partial reasoning',
                'final_output':'','forced_reasoning_end':False}
    control='\n</think>\n\n' if not closings else ''
    remaining=max_seconds-(perf_counter()-started)
    if remaining<=0:
        return {**first,'segments':[first],'protocol_error':'reasoning exhausted total wall-time budget',
                'final_output':'','forced_reasoning_end':False}
    continuation=prompt+raw+control
    second=generate(continuation,answer_budget,thinking=False,sampling=sampling,
                    seed=None if seed is None else seed+104729,max_seconds=remaining)
    combined=raw+control+second['output']
    result={'output':combined,'raw_output':first['raw_output']+control+second['raw_output'],
            'output_ids':first['output_ids']+second['output_ids'],
            'input_tokens':first['input_tokens']+second['input_tokens'],
            'output_tokens':first['output_tokens']+second['output_tokens'],
            'ttft_ms':first['ttft_ms'],'elapsed_ms':(perf_counter()-started)*1000,
            'model_elapsed_ms':first['elapsed_ms']+second['elapsed_ms'],
            'segments':[first,second],'forced_reasoning_end':bool(control),
            'injected_control_text':control,'injected_control_tokens':len(tokenizer.encode(control,add_special_tokens=False)),
            'reasoning_budget':reasoning_budget,'answer_budget':answer_budget,
            'stopped_on_eos':second.get('stopped_on_eos',False),'final_output':'',
            'thinking':True,'seed':seed,'sampling':sampling}
    try:
        if not result['stopped_on_eos']: raise ValueError('final completion stopped without EOS')
        result['final_output']=final_answer(combined,thinking=True)
        if not result['final_output']: raise ValueError('empty final completion')
        end_id=tokenizer.convert_tokens_to_ids('</think>')
        positions=[i for i,x in enumerate(first['output_ids']) if x==end_id]
        result['reasoning_tokens']=first['output_tokens'] if control else positions[0]+1
        result['final_answer_tokens']=result['output_tokens']-result['reasoning_tokens']
    except (ValueError,IndexError) as error:
        result.update(final_output='',protocol_error=str(error))
    return result
