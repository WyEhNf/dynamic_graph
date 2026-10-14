import unittest

from context_governance.bundles import dependency_map, source_chunks
from context_governance.core import ByteEstimate, Item, govern


class InitializationDependencies(unittest.TestCase):
    def retained_value(self,source,expression):
        items=source_chunks('helpers.py',source)
        target=Item('solution.py','code','from helpers import result\ndef solve(): return result()\n',True)
        items.append(target)
        graph=dependency_map(items)
        kept=govern('fix solve',items,10000,ByteEstimate(),graph)['selected']
        actual={}; full={}
        exec(source,full)
        exec(''.join(row['text'] for row in kept if row['id'].startswith('helpers.py')),actual)
        self.assertEqual(eval(expression,actual),eval(expression,full))
        return {row['id'] for row in kept}

    def test_augassign_and_module_loop_target(self):
        self.retained_value('scale=2\nscale*=7\ndef result():\n    return scale\n','result()')
        self.retained_value('for coefficient in [2,5]:\n    pass\ndef result():\n    return coefficient\n','result()')

    def test_mutating_initializer_and_indirect_global_assignment(self):
        self.retained_value('data=[]\ndata.append(11)\ndef result():\n    return data[:]\n','result()')
        self.retained_value('scale=1\ndef initialize():\n    global scale\n    scale=13\ninitialize()\ndef result():\n    return scale\n','result()')

    def test_module_named_expression_and_subscript_assignment(self):
        self.retained_value('(limit:=3)\ndef result():\n    return limit\n','result()')
        self.retained_value('data=[0]\ndata[0]=17\ndef result():\n    return data[:]\n','result()')

    def test_unrelated_function_defaults_can_initialize_global_state(self):
        self.retained_value('data=[]\ndef initialize():\n    data.append(19)\n    return 0\ndef unrelated(value=initialize()):\n    return value\ndef result():\n    return data[:]\n','result()')

    def test_function_local_binding_is_not_exported(self):
        source='x=4\ndef unrelated():\n    x=999\n    return x\ndef result():\n    return x\n'
        kept=self.retained_value(source,'result()')
        self.assertNotIn('helpers.py:2-4',kept)


if __name__=='__main__': unittest.main()
