"""Conservative draft hints derived only from visible requirements and AST.

These are review hints, not proof of correctness or a replacement for tests.
No execution, expected output, hidden fixture, or evaluation result is used.
"""
import ast
import re


def _code(text):
    blocks=re.findall(r'```(?:python|py)?\s*\n(.*?)```',text,re.S|re.I)
    return max(blocks,key=len) if blocks else text.strip()


def audit_draft(spec, draft, existing_target):
    try: tree=ast.parse(_code(draft))
    except SyntaxError as error:
        return [f'The draft has a Python syntax error at line {error.lineno}: {error.msg}. Return a complete syntactically valid file.']
    findings=[]; lower=spec.lower()
    immutability=bool(re.search(r'(do not|never|without)\s+(modify|mutate|modifying)|never mutate',lower))
    fresh='new list' in lower
    target_names=set(re.findall(r'\bImplement\s+([A-Za-z_]\w*)\s*\(',spec))
    functions=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
               and (not target_names or node.name in target_names)]
    for function in functions:
        parameters={arg.arg for arg in function.args.posonlyargs+function.args.args+function.args.kwonlyargs}
        local_stores={node.id for node in ast.walk(function) if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Store)}
        for node in ast.walk(function):
            if immutability and isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                owner=node.func.value
                if isinstance(owner,ast.Name) and owner.id in parameters-local_stores and node.func.attr in {'sort','reverse','clear','extend','append','pop','remove','insert'}:
                    findings.append(f'Line {node.lineno} calls {owner.id}.{node.func.attr} on an input parameter. The requirements forbid modifying input; review that operation.')
            if fresh and isinstance(node,ast.Return) and isinstance(node.value,ast.Name) and node.value.id in parameters-local_stores:
                findings.append(f'Line {node.lineno} returns the input parameter {node.value.id} itself. The requirements ask for a new list, including no-op cases; review object identity.')
    called={node.func.id for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
    helpers=[]
    for node in tree.body:
        if isinstance(node,ast.ImportFrom) and node.module=='helpers':
            helpers += [(alias.name,alias.asname or alias.name) for alias in node.names if alias.name!='*']
    for name,alias in helpers:
        if re.search(r'\b'+re.escape(name)+r'\b',spec) and alias not in called:
            findings.append(f'The user explicitly mentions helper {name}; it is imported as {alias} but no direct call appears in the draft. Verify required helper use, not merely the import.')
    raises_value_error=any(isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and isinstance(node.exc.func,ast.Name) and node.exc.func.id=='ValueError' for node in ast.walk(tree))
    if re.search(r'raises?\s+valueerror',lower) and not raises_value_error and not any(alias in called for _,alias in helpers):
        findings.append('The requirements include ValueError for invalid input, but the draft has no explicit ValueError raise or direct imported-helper call. Review validation paths; builtin conversions may cover only some conditions.')
    if re.search(r'raises?\s+valueerror',lower):
        for node in ast.walk(tree):
            if not isinstance(node,ast.ExceptHandler): continue
            caught={part.id for part in ast.walk(node.type) if isinstance(part,ast.Name)} if node.type else {'BaseException'}
            if caught & {'ValueError','Exception','BaseException'} and any(isinstance(part,ast.Return) for statement in node.body for part in ast.walk(statement)):
                findings.append(f'Line {node.lineno} catches a possible ValueError and returns a normal result. The requirements ask invalid input to raise ValueError; inspect whether that handler swallows the required exception.')
    if 'not silently skip invalid' in lower:
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in {'isdigit','isnumeric','isdecimal'}:
                findings.append(f'Line {node.lineno} uses {node.func.attr}. A digit filter may silently discard invalid fields or signed integers. Check the requirement to convert every nonblank field and propagate invalid conversions.')
                break
    if 'preserve the existing' in lower and existing_target:
        try: original=ast.parse(existing_target)
        except SyntaxError: original=None
        if original:
            def bindings(nodes):
                result={}
                for node in nodes:
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                        result[node.name]=node
                    elif isinstance(node,(ast.Assign,ast.AnnAssign)):
                        targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                        for target in targets:
                            if isinstance(target,ast.Name): result[target.id]=node
                return result
            current=bindings(tree.body)
            for name,node in bindings(original.body).items():
                if name in target_names or not re.search(r'\b'+re.escape(name)+r'\b',spec): continue
                if name not in current or ast.dump(node,include_attributes=False)!=ast.dump(current[name],include_attributes=False):
                    findings.append(f'Existing export {name} is explicitly required unchanged, but its definition is missing or structurally changed. Preserve it while repairing the requested target.')
    return list(dict.fromkeys(findings))
