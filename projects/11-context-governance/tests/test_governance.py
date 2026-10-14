import unittest
from context_governance.core import ByteEstimate, Item, govern, render
from context_governance.evaluation import run_stream


class GovernanceTests(unittest.TestCase):
    def test_pins_preserved_and_budget_accounted(self):
        items = [Item("spec", "requirement", "必须保存所有约束", True),
                 Item("noise", "memory", "irrelevant" * 100),
                 Item("code", "code", "fix parser error", False, 1)]
        result = govern("fix parser error", items, 120)
        self.assertIn("必须保存所有约束", result["context"])
        self.assertLessEqual(ByteEstimate().count(result["context"]), 120)
        self.assertEqual(result["metrics"]["generation_quality"], "not_evaluated")
        self.assertIsNone(result["metrics"]["ttft_ms"])

    def test_oversized_pins_fail_instead_of_silent_truncation(self):
        with self.assertRaisesRegex(ValueError, "protected"):
            govern("task", [Item("p", "requirement", "a" * 100, True)], 10)

    def test_exact_duplicates_and_tool_error(self):
        tool = "\n".join(["progress completed"] * 200 + ["ERROR parser: malformed token"])
        result = govern("parser", [Item("a", "memory", "parser detail"),
                                    Item("b", "memory", "parser detail"),
                                    Item("log", "tool", tool)], 120)
        self.assertEqual(result["decisions"]["b"], "exact_duplicate")
        self.assertIn("ERROR parser: malformed token", result["context"])

    def test_unicode_budget_and_empty(self):
        self.assertEqual(govern("", [], 10)["metrics"]["estimated_reduction"], 0)
        items = [Item("1", "code", "中文" * 20)]
        result = govern("中文", items, 10)
        self.assertEqual(result["metrics"]["output_units"], 0)

    def test_different_kinds_and_source_identity_are_preserved(self):
        items = [Item("requirement", "requirement", "same", True),
                 Item("file_a", "code", "same"), Item("file_b", "code", "same"),
                 Item("memory", "memory", "same")]
        result = govern("same", items, 1000)
        self.assertEqual([x["id"] for x in result["selected"]],
                         [x.id for x in items])

    def test_order_sensitive_counter_is_checked_in_output_order(self):
        class OrderCounter:
            name = "order-sensitive-test-counter"
            def count(self, text):
                # Simulate tokenizer boundary effects after restoring source order.
                return 99 if text.startswith("[code:early]") else len(text)
        items = [Item("early", "code", "x"),
                 Item("pin", "requirement", "must", True)]
        result = govern("x", items, 50, OrderCounter())
        self.assertEqual(result["decisions"]["early"], "budget_drop")
        self.assertLessEqual(result["metrics"]["output_units"], 50)

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            govern("task", [Item("id", "code", "a"), Item("id", "code", "b")], 100)

    def test_missing_model_content_cannot_fake_ttft(self):
        class Empty:
            def stream(self, context):
                yield ""
        with self.assertRaises(ValueError):
            run_stream(Empty(), "ctx")

    def test_screening_keeps_atomic_dependency_cycles(self):
        items=[Item('pin','requirement','repair parser',True),
               Item('a','code','def parser(): return helper()',False,1),
               Item('b','code','def helper(): return parser()')]
        result=govern('repair parser',items,500,dependencies={'a':['b'],'b':['a']})
        self.assertEqual({x['id'] for x in result['selected']},{'pin','a','b'})

    def test_batch_screen_reduces_exact_recounts_without_budget_leak(self):
        class CountingCounter(ByteEstimate):
            count_calls=0
            def count(self,text):
                self.count_calls+=1
                return super().count(text)
            def count_many(self,texts):
                return [len(x.encode('utf-8')) for x in texts]
        counter=CountingCounter()
        items=[Item('pin','requirement','repair parser',True)]
        items.extend(Item(str(i),'code','parser '+ 'x'*200) for i in range(200))
        result=govern('parser',items,300,counter)
        self.assertLess(counter.count_calls,15)
        self.assertLessEqual(counter.count(result['context']),300)

    def test_generic_task_words_do_not_fill_with_unrelated_code(self):
        items=[Item('pin','requirement','Implement slug(text). Return a complete file.',True),
               Item('legacy.py','code','def unused(values): return values')]
        result=govern('Implement slug(text). Return a complete file.',items,500)
        self.assertEqual(result['decisions']['legacy.py'],'irrelevant_drop')

    def test_identifiers_match_concepts_with_dependencies(self):
        items=[Item('ParserValue.py','code','def parser_value(x): return CONSTANT + x'),
               Item('constant.py','code','CONSTANT = 3'),Item('other','code','def telemetry(x): return x')]
        result=govern('repair parser',items,500,dependencies={'ParserValue.py':['constant.py']})
        self.assertEqual({x['id'] for x in result['selected']},{'ParserValue.py','constant.py'})

    def test_file_extensions_are_not_relevance_signals(self):
        items=[Item('target.py','code','def parser_value(x): return x',True),
               Item('irrelevant.py:1-2','code','def telemetry_item(x): return x')]
        result=govern('Repair parser in target.py. Return complete Python file.',items,500)
        self.assertEqual(result['decisions']['irrelevant.py:1-2'],'irrelevant_drop')

    def test_request_can_omit_diagnostic_input_count_but_budget_stays_exact(self):
        result=govern('parser',[Item('pin','requirement','parser',True),Item('code','code','parser')],100,
                      measure_input=False)
        self.assertIsNone(result['metrics']['input_units'])
        self.assertIsNone(result['metrics']['estimated_reduction'])
        self.assertEqual(result['metrics']['output_units'],ByteEstimate().count(result['context']))


if __name__ == "__main__":
    unittest.main()
