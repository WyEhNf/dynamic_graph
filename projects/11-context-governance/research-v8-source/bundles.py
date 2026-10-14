"""Reproducible local engineering snapshots, with no Git-history dependency."""
import ast
import hashlib
import json
from pathlib import Path

from .core import Item


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b'\0' + path.read_bytes())
    return digest.hexdigest()


def source_chunks(path: str, text: str) -> list[Item]:
    """Keep imports, decorators and whole top-level definitions; never cut functions."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [Item(path, 'code', text)]
    lines = text.splitlines(keepends=True)
    chunks = []
    intervals = []
    for node in tree.body:
        start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])]) - 1
        end = node.end_lineno
        if intervals and start < intervals[-1][1]:
            intervals[-1] = (intervals[-1][0], max(end, intervals[-1][1]))
        else:
            intervals.append((start,end))
    cursor = 0
    for start,end in intervals:
        if start > cursor:
            chunks.append(Item(f'{path}:{cursor+1}-{start}', 'code', ''.join(lines[cursor:start])))
        chunks.append(Item(f'{path}:{start+1}-{end}', 'code', ''.join(lines[start:end])))
        cursor = end
    if cursor < len(lines):
        chunks.append(Item(f'{path}:{cursor+1}-{len(lines)}', 'code', ''.join(lines[cursor:])))
    return chunks or [Item(path, 'code', text)]


def dependency_map(items):
    """Conservative Python global/import closure across snapshot source chunks."""
    by_module = {}
    parsed = {}
    exports = {}
    packages=set()
    def binding_statements(nodes):
        for node in nodes:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Assign,ast.AnnAssign,ast.Import,ast.ImportFrom)):
                yield node
            else:
                for field in ['body','orelse','finalbody']:
                    children=getattr(node,field,[])
                    if isinstance(children,list): yield from binding_statements(children)
                for handler in getattr(node,'handlers',[]): yield from binding_statements(handler.body)
                for case in getattr(node,'cases',[]): yield from binding_statements(case.body)
    for item in items:
        if item.kind!='code': continue
        filename=item.id.split(':')[0]
        module = filename.removesuffix('.py').replace('/','.')
        if module.endswith('.__init__'):
            module=module.removesuffix('.__init__'); packages.add(module)
        try: tree=ast.parse(item.text)
        except SyntaxError: continue
        parsed[item.id]=(module,tree)
        by_module.setdefault(module,[]).append(item.id)
        for node in binding_statements(tree.body):
            names=[]
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): names=[node.name]
            elif isinstance(node,(ast.Assign,ast.AnnAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                names=[n.id for target in targets for n in ast.walk(target) if isinstance(n,ast.Name)]
            elif isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[a.asname or (a.name.split('.')[0] if isinstance(node,ast.Import) else a.name) for a in node.names]
            for name in names: exports.setdefault((module,name),[]).append(item.id)
    def imported_module(module,node):
        if not node.level: return node.module or ''
        base=module if module in packages else module.rpartition('.')[0]
        parts=base.split('.') if base else []
        if node.level>1: parts=parts[:max(0,len(parts)-node.level+1)]
        return '.'.join(parts+([node.module] if node.module else []))
    stars={}
    for item_id,(module,tree) in parsed.items():
        if any(isinstance(n,ast.ImportFrom) and any(a.name=='*' for a in n.names) for n in binding_statements(tree.body)):
            stars.setdefault(module,[]).append(item_id)
    dependencies={}
    for item_id,(module,tree) in parsed.items():
        required=set()
        if any(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) for n in ast.walk(tree)):
            required.update(stars.get(module,[]))
        for node in ast.walk(tree):
            if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Load):
                required.update(exports.get((module,node.id),[]))
            elif isinstance(node,ast.ImportFrom):
                target=imported_module(module,node)
                for alias in node.names:
                    if alias.name=='*': required.update(by_module.get(target,[]))
                    else:
                        required.update(exports.get((target,alias.name),[]))
                        required.update(by_module.get(target+'.'+alias.name,[]))
            elif isinstance(node,ast.Import):
                for alias in node.names: required.update(by_module.get(alias.name,[]))
        required.discard(item_id)
        if required: dependencies[item_id]=sorted(required)
    return dependencies


def load_case(suite: Path, case_id: str):
    metadata = json.loads((suite / 'metadata' / f'{case_id}.json').read_text(encoding='utf-8'))
    spec = (suite / 'spec' / f'{case_id}.md').read_text(encoding='utf-8')
    root = suite / 'repo_bundles' / metadata['baseline_bundle']
    if digest_tree(root) != metadata['snapshot_sha256']:
        raise ValueError('snapshot checksum mismatch')
    items = [Item('requirements', 'requirement', spec, True)]
    pins = set(metadata['pinned_files'])
    for path in sorted(root.rglob('*.py')):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding='utf-8')
        if relative in pins:
            items.append(Item(relative, 'code', text, True))
        else:
            items.extend(source_chunks(relative, text))
    history = metadata.get('history', [])
    items.extend(Item(f'history-{i}', x['kind'], x['text'], x.get('protected', False), x.get('utility', 0.0))
                 for i, x in enumerate(history))
    metadata['context_dependencies']=dependency_map(items)
    return metadata, root, spec, items
