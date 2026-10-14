"""Token-level termination checks for greedy and reasoning code candidates."""
from dataclasses import asdict
import math


def validate_sampling(sampling):
    if sampling is None: return {'do_sample': False}
    if not isinstance(sampling, dict) or set(sampling) != {'temperature', 'top_p', 'top_k'}:
        raise ValueError('sampling requires exactly temperature, top_p and top_k')
    temperature, top_p, top_k = (sampling[k] for k in ('temperature', 'top_p', 'top_k'))
    for value in (temperature, top_p):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('sampling numbers must be finite')
    if temperature <= 0 or not 0 < top_p <= 1 or type(top_k) is not int or top_k < 1:
        raise ValueError('invalid sampling range')
    return {'do_sample': True, **sampling}


def generation_record(generated, ids, tokenizer, eos_token_id, *, thinking=False, seed=None, sampling=None):
    from .candidate_gate import final_answer
    result = asdict(generated)
    eos = set(eos_token_id if isinstance(eos_token_id, (list, tuple)) else [eos_token_id])
    result.update(output_ids=list(ids), stopped_on_eos=bool(ids and ids[-1] in eos),
                  raw_output=tokenizer.decode(ids, skip_special_tokens=False),
                  seed=seed, sampling=sampling, thinking=thinking, final_output='')
    try:
        if not result['stopped_on_eos']:
            raise ValueError('generation stopped without EOS; incomplete candidate rejected')
        text = tokenizer.decode(ids, skip_special_tokens=True)
        # Qwen3 reasoning delimiters are ordinary tokens, so skip_special_tokens
        # preserves the boundary. Validate exactly once before code extraction.
        result['final_output'] = final_answer(text, thinking=thinking)
        if not result['final_output']:
            raise ValueError('empty final answer')
        if thinking:
            closing = tokenizer.convert_tokens_to_ids('</think>')
            boundaries = [i for i, token in enumerate(ids) if token == closing]
            if len(boundaries) != 1:
                raise ValueError('reasoning boundary token count is not one')
            result['reasoning_tokens'] = boundaries[0] + 1
            result['final_answer_tokens'] = len(ids) - boundaries[0] - 1
        else:
            result['reasoning_tokens'] = 0
            result['final_answer_tokens'] = len(ids)
    except ValueError as error:
        result['final_output'] = ''
        result['protocol_error'] = str(error)
    return result
