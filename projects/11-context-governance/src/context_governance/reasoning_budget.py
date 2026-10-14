"""Single-pass reasoning boundary control; keeps the active model KV cache."""


class ReasoningBudget:
    def __init__(self, closing_token_id, reasoning_tokens, answer_tokens):
        for value in (closing_token_id, reasoning_tokens, answer_tokens):
            if type(value) is not int or value < 0: raise ValueError('budget values must be nonnegative integers')
        if reasoning_tokens < 1 or answer_tokens < 1: raise ValueError('token budgets must be positive')
        self.closing_token_id=closing_token_id
        self.reasoning_tokens=reasoning_tokens
        self.answer_tokens=answer_tokens
        self.prompt_length=None
        self.observed=0
        self.closing_position=None
        self.forced_positions=[]

    def observe(self, input_ids):
        if input_ids.shape[0]!=1: raise ValueError('reasoning budget supports one request at a time')
        length=input_ids.shape[-1]
        if self.prompt_length is None:
            self.prompt_length=length
            self.observed=length
        if length < self.observed: raise ValueError('generation sequence shrank')
        # Examine each emitted token once. Do not copy the growing KV prefix to
        # CPU every decoding step or inspect closing tags in the input prompt.
        for offset,token in enumerate(input_ids[0,self.observed:length].tolist(),self.observed):
            if token==self.closing_token_id and self.closing_position is None:
                self.closing_position=offset-self.prompt_length
        self.observed=length
        return length-self.prompt_length

    def __call__(self,input_ids,scores):
        generated=self.observe(input_ids)
        if self.closing_position is None and generated>=self.reasoning_tokens:
            scores.fill_(-float('inf'))
            scores[:,self.closing_token_id]=0
            self.forced_positions.append(generated)
        return scores

    def answer_limit_reached(self,input_ids,scores,**kwargs):
        generated=self.observe(input_ids)
        return (self.closing_position is not None
                and generated-self.closing_position-1>=self.answer_tokens)
