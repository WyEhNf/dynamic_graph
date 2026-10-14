"""Public-only repair conversations, with an explicit final correction request.

The prompt builder receives no hidden test path or hidden evaluator result.
Keep compression/governance evidence separate from the generation prompt.
"""
from .local_model import CONCISE_SYSTEM


def candidate_messages(context, requirements, *, previous=None, public_tests='', feedback=''):
    messages=[{'role':'system','content':CONCISE_SYSTEM +
        ' Preserve existing exports and dependency calls required by the public task. '
        'Pure function fixture: no attribute writes or process introspection.'},
        {'role':'user','content':'CONTEXT:\n'+context+'\n\nMANDATORY REQUIREMENTS:\n'+requirements+
            '\n\nImplement every requirement and return the complete target Python file.'}]
    if previous is not None:
        messages += [{'role':'assistant','content':previous},
            {'role':'user','content':'The previous candidate failed these trusted public checks.\n\n'+
                'TRUSTED PUBLIC TESTS:\n'+public_tests+'\n\nACTUAL PUBLIC FEEDBACK:\n'+feedback+
                '\n\nMANDATORY REQUIREMENTS:\n'+requirements+
                '\n\nCorrect the observed failures, preserve all required existing exports, '
                'and return the complete corrected target Python file. Do not repeat the failed draft.'}]
    return messages
