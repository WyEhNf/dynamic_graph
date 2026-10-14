import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from context_governance.core import ByteEstimate, Item, govern
from context_governance.typescript_context import TypeScriptContext


ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / 'adapters/typescript/node_modules/typescript/bin/tsc'


@unittest.skipUnless(shutil.which('node') and COMPILER.exists(), 'optional TypeScript compiler not installed')
class TypeScriptAdapterTests(unittest.TestCase):
    def selected(self, adapter, files, pins=('main.ts',)):
        result = adapter.analyze(files, pins)
        items = [Item('task', 'requirement', 'Preserve run and its dependencies.', True), *result['items']]
        selected = govern('Preserve run and its dependencies.', items, 4000, ByteEstimate(), result['dependencies'])
        sources = {}
        for item in selected['selected']:
            if item['kind'] == 'code':
                sources.setdefault(item['id'].split(':')[0], []).append(item['text'])
        return result, {name: ''.join(pieces) for name, pieces in sources.items()}

    def compile_and_run(self, sources, expected):
        with tempfile.TemporaryDirectory(prefix='hackathon11-ts-') as directory:
            root = Path(directory)
            for name, text in sources.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
            compiled = subprocess.run([shutil.which('node'), str(COMPILER), '--target', 'ES2022', '--module', 'commonjs',
                                       '--strict', '--skipLibCheck', '--ignoreDeprecations', '6.0', '--outDir', 'build',
                                       *sorted(sources)], cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            test = 'const m=require("./build/main.js"); if(m.run({value:2})!==' + str(expected) + ')throw Error("semantic mismatch");'
            executed = subprocess.run([shutil.which('node'), '-e', test], cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)

    def test_compiled_transitive_types_initialization_and_cache_edits(self):
        files = {'main.ts': 'import {twice} from "./barrel";\nimport type {Payload} from "./types";\nexport function run(x:Payload){return twice(x.value);}\n',
                 'barrel.ts': 'export {twice} from "./helpers";\n',
                 'types.ts': 'export interface Payload {value:number;}\n',
                 'config.ts': 'export let LIMIT=8;\nLIMIT+=8;\n',
                 'helpers.ts': 'import {LIMIT} from "./config";\nfunction hidden(x:number){return x*2;}\nexport function twice(x:number){return hidden(x)+LIMIT;}\n',
                 'unrelated.ts': 'export function unused(x:number){return x-1000;}\n'}
        with TypeScriptContext() as adapter:
            result, sources = self.selected(adapter, files)
            self.assertFalse(result['conservative_full_project_fallback'])
            self.assertNotIn('unrelated.ts', sources)
            self.compile_and_run(sources, 20)
            self.assertTrue(adapter.analyze(files, ['main.ts'])['cache_hit'])
            changed = dict(files)
            changed['helpers.ts'] = changed['helpers.ts'].replace('x*2', 'x*3')
            result, revised = self.selected(adapter, changed)
            self.assertFalse(result['cache_hit'])
            self.compile_and_run(revised, 22)
            self.assertEqual(files['helpers.ts'].count('x*2'), 1)

    def test_source_roundtrip_unicode_comments_classes_and_empty_files(self):
        cases = ['// 🌟 中文\r\nexport interface Box {value:number;}\r\n/** Keep. */\r\nexport function f(x:Box){return x.value;}\r\n// tail\r\n',
                 'export class Box {static value=3; method(){return Box.value;}}\n',
                 'export namespace Numbers {export const n=4;}\nexport type N=typeof Numbers.n;\n', '',
                 'export const node=<span>中文</span>;\n']
        with TypeScriptContext() as adapter:
            for index, text in enumerate(cases):
                name = f'case{index}.tsx' if index == 4 else f'case{index}.ts'
                result = adapter.analyze({name: text})
                self.assertEqual(''.join(item.text for item in result['items']), text)

    def test_type_only_import_avoids_unrelated_types_without_losing_references(self):
        files = {'main.ts': 'import type {Payload} from "./types"; export function run(x:Payload){return x.value*2;}',
                 'types.ts': 'export interface Base {value:number;}\nexport interface Payload extends Base {}\n' +
                             ''.join(f'export interface Unused{index} {{unused{index}:number;}}\n' for index in range(500))}
        with TypeScriptContext() as adapter:
            result, sources = self.selected(adapter, files)
            self.assertFalse(result['conservative_full_project_fallback'])
            self.assertIn('interface Base', sources['types.ts'])
            self.assertIn('interface Payload', sources['types.ts'])
            self.assertNotIn('interface Unused', sources['types.ts'])
            self.compile_and_run(sources, 4)

    def test_dynamic_missing_modules_and_arkts_fall_back(self):
        cases = [{'main.ts': 'const name="./helper"; export async function run(){return import(name);}',
                  'helper.ts': 'export const x=1;'},
                 {'main.ts': 'import {x} from "./missing"; export function run(){return x;}',
                  'helper.ts': 'export const x=1;'},
                 {'main.ts': 'export function run(){return 1;}',
                  'screen.ets': '@Entry\n@Component\nstruct Screen {build(){Column(){Text("hello")}}}'}]
        with TypeScriptContext() as adapter:
            for files in cases:
                result = adapter.analyze(files, ['main.ts'])
                self.assertTrue(result['conservative_full_project_fallback'])
                with self.assertRaises(ValueError):
                    govern('run', result['items'], 10, ByteEstimate(), result['dependencies'])
                _, selected = self.selected(adapter, files)
                self.assertEqual(selected, files)

    def test_invalid_paths_rejected_without_poisoning_worker(self):
        with TypeScriptContext() as adapter:
            for files, pins in [({'../outside.ts': ''}, []), ({'/absolute.ts': ''}, []),
                                ({'nested/../file.ts': ''}, []), ({'main.ts': ''}, ['missing.ts'])]:
                with self.assertRaises(ValueError):
                    adapter.analyze(files, pins)
            result = adapter.analyze({'main.ts': 'export const answer=42;'}, ['main.ts'])
            self.assertEqual(result['items'][0].text, 'export const answer=42;')


if __name__ == '__main__':
    unittest.main()
