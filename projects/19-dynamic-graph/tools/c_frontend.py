"""Typed Clang AST lowering; stack instructions and symbolic access IR."""
from __future__ import annotations
from contextlib import contextmanager
from collections import Counter
import math


def walk(node):
    yield node
    for child in node.get("inner", []):
        yield from walk(child)


def unwrap(node):
    while node.get("kind") in ("ImplicitCastExpr", "ParenExpr"):
        if node.get("kind") == "ImplicitCastExpr" and node.get("castKind") == "FloatingToIntegral":
            break
        node = node["inner"][0]
    return node


def scalar_type(node):
    spelling = node.get("type", {}).get("qualType", "").replace("const ", "")
    # Reject unsigned wraparound, wide integer precision and bool conversion
    # instead of silently approximating those C types with the VM's doubles.
    if spelling == "int":
        return "int"
    if spelling == "double":
        return "double"
    raise ValueError(f"unsupported scalar type {spelling!r}")


def integer_expression(op,left,right):
    """Canonicalize commutative integer index operands, never FP arithmetic."""
    if op in ('+','*') and repr(left)>repr(right):left,right=right,left
    return [op,left,right]


class Compiler:
    def __init__(self, function, definitions=None):
        self.function = function
        self.definitions = definitions or {}
        self.bindings = {}
        self.call_stack = []
        self.symbol_depth = 0
        self.symbol_steps = 0
        self.native_helpers_safe = True
        self.parameters = [c for c in function["inner"] if c.get("kind") == "ParmVarDecl"]
        types = [p["type"]["qualType"] for p in self.parameters]
        if len(types) not in (3, 4) or types[0] not in ("const double *", "double *") or types[1:3] != ["double *", "int"] or (len(types) == 4 and types[3] != "int"):
            raise ValueError("supported signature: int/void f(const double *input, double *output, int n[, int block_size])")
        if not function["type"]["qualType"].startswith(("int (", "void (")):
            raise ValueError("function return type must be int or void")
        self.arrays = {self.parameters[0]["id"]: 0, self.parameters[1]["id"]: 1}
        self.slots = {}
        self.names = {}
        self.types = {}
        self.code = []
        self.loops = []
        self.accesses = []
        self.loop_stack = []
        for parameter in self.parameters[2:]:
            self.declare(parameter)
        self.shape_slot = self.slots[self.parameters[2]["id"]]
        self.block_slot = self.slots[self.parameters[3]["id"]] if len(self.parameters) == 4 else -1
        self.optimized = "none"

    def declare(self, declaration):
        key = declaration["id"]
        if key not in self.slots:
            if len(self.slots)>=4096:raise ValueError('metadata scalar slot limit exceeded')
            self.slots[key] = len(self.slots)
            self.names[key] = declaration["name"]
            self.types[key] = scalar_type(declaration)
        return self.slots[key]

    def emit(self, op, arg=0):
        if len(self.code)>=100000:raise ValueError('metadata instruction limit exceeded during lowering')
        self.code.append([op, arg])
        return len(self.code) - 1

    def patch(self, index):
        self.code[index][1] = len(self.code)

    @contextmanager
    def inline_helper(self, node):
        callee = unwrap(node["inner"][0]).get("referencedDecl", {})
        key = callee.get("id")
        if key not in self.definitions:
            raise ValueError(f"unsupported or recursive helper {callee.get('name')!r}")
        definition = self.definitions[key]
        key=definition['id']
        if key in self.call_stack:raise ValueError(f"unsupported or recursive helper {callee.get('name')!r}")
        parameters = [c for c in definition["inner"] if c.get("kind") == "ParmVarDecl"]
        body = next(c for c in definition["inner"] if c.get("kind") == "CompoundStmt")
        statements = body.get("inner", [])
        if len(parameters) != len(node["inner"]) - 1 or any(scalar_type(p) not in ("int", "double") for p in parameters) or not statements or statements[-1].get("kind") != "ReturnStmt" or len(statements[-1].get("inner", [])) != 1:
            raise ValueError("helpers must be pure scalar SSA declarations followed by one return expression")
        previous = self.bindings.copy()
        self.bindings.update({parameter["id"]: argument for parameter, argument in zip(parameters, node["inner"][1:])})
        self.call_stack.append(key)
        try:
            local_ids={declaration['id']for statement in statements[:-1]if statement.get('kind')=='DeclStmt'for declaration in statement.get('inner',[])if declaration.get('kind')=='VarDecl'}
            for statement in statements[:-1]:
                if statement.get('kind')!='DeclStmt':raise ValueError('helper side effects, branches and repeated assignments are unsupported')
                for declaration in statement.get('inner',[]):
                    if declaration.get('kind')!='VarDecl' or len(declaration.get('inner',[]))!=1:raise ValueError('helper locals must have one initializer')
                    target_type=scalar_type(declaration);initializer=declaration['inner'][0]
                    for reference in walk(initializer):
                        referenced=reference.get('referencedDecl',{}).get('id')
                        if referenced in local_ids and referenced not in self.bindings:raise ValueError('helper local read before initialization')
                    # A local int stores after C conversion, even when its value
                    # is substituted into a double expression later.
                    if target_type!=scalar_type(unwrap(initializer)):
                        initializer={'kind':'CStyleCastExpr','type':{'qualType':target_type},'inner':[initializer]}
                    self.bindings[declaration['id']]=initializer
            yield statements[-1]["inner"][0]
        finally:
            self.call_stack.pop(); self.bindings = previous

    def symbol(self, node):
        if self.symbol_depth==0:self.symbol_steps=0
        self.symbol_steps+=1
        if self.symbol_steps>10000 or self.symbol_depth>=128:raise ValueError('symbolic expression resource limit exceeded')
        self.symbol_depth+=1
        try:return self._symbol(node)
        finally:self.symbol_depth-=1

    def _symbol(self, node):
        """Normalized typed symbolic expression, stable across variable renaming."""
        node = unwrap(node)
        kind = node.get("kind")
        inner = node.get("inner", [])
        if kind == "DeclRefExpr":
            key = node["referencedDecl"]["id"]
            if key in self.bindings: return self.symbol(self.bindings[key])
            if key in self.arrays:
                return ["array", self.arrays[key]]
            if key not in self.slots:
                raise ValueError("reference to unsupported global, alias, or undeclared local")
            return ["slot", self.slots[key]]
        if kind in ("IntegerLiteral", "FloatingLiteral"):
            return ["constant", float(node["value"])]
        if kind == "ArraySubscriptExpr":
            return ["read", self.array_id(inner[0]), self.symbol(inner[1])]
        if kind in ("BinaryOperator", "CompoundAssignOperator"):
            left,right=self.symbol(inner[0]),self.symbol(inner[1]);op=node['opcode']
            return integer_expression(op,left,right) if scalar_type(node)=='int' else [op,left,right]
        if kind == "UnaryOperator":
            return [node["opcode"], self.symbol(inner[0])]
        if kind == "CallExpr":
            callee = unwrap(inner[0])
            if callee.get("referencedDecl", {}).get("id") in self.definitions:
                # Evaluate argument symbols before entering the callee body:
                # h(h(x)) is composition, whereas a body calling itself recurs.
                arguments=[self.symbol(argument)for argument in inner[1:]]
                definition=self.definitions[callee['referencedDecl']['id']]
                parameters=[child for child in definition['inner']if child.get('kind')=='ParmVarDecl']
                with self.inline_helper(node) as expression:
                    self.bindings.update({parameter['id']:{'kind':'SymbolicValue','value':argument}for parameter,argument in zip(parameters,arguments)})
                    return self.symbol(expression)
            return ["call", callee.get("referencedDecl", {}).get("name"), *[self.symbol(c) for c in inner[1:]]]
        if kind == "ConditionalOperator":
            return ["select", *[self.symbol(c) for c in inner]]
        if kind in ("CStyleCastExpr", "ImplicitCastExpr"):
            return ["cast", scalar_type(node), self.symbol(inner[0])]
        if kind=='SymbolicValue':return node['value']
        raise ValueError(f"unsupported expression {kind}")

    def array_id(self, node):
        node = unwrap(node)
        if node.get("kind") != "DeclRefExpr" or node.get("referencedDecl", {}).get("id") not in self.arrays:
            raise ValueError("only direct input/output array subscripts are supported; aliases require separate analysis")
        return self.arrays[node["referencedDecl"]["id"]]

    def access(self, node, mode):
        node = unwrap(node)
        inner = node["inner"]
        array = self.array_id(inner[0])
        self.accesses.append({"mode": mode, "array": "input" if array == 0 else "output", "index": self.symbol(inner[1]), "loop_ids": list(self.loop_stack)})
        return array, inner[1]

    def expr(self, node):
        node = unwrap(node)
        kind = node.get("kind")
        inner = node.get("inner", [])
        if kind in ("IntegerLiteral", "FloatingLiteral"):
            scalar_type(node)
            value=float(node['value'])
            if not math.isfinite(value):raise ValueError('non-finite literal is outside the Metadata constant contract')
            self.emit("CONST", value)
        elif kind == "DeclRefExpr":
            key = node["referencedDecl"]["id"]
            if key in self.bindings:
                self.expr(self.bindings[key]); return
            if key not in self.slots:
                raise ValueError("scalar expression references an unsupported symbol")
            self.emit("LOAD", self.slots[key])
        elif kind == "ArraySubscriptExpr":
            array, index = self.access(node, "read")
            self.expr(index)
            self.emit("READ", array)
        elif kind == "BinaryOperator":
            op = node["opcode"]
            if op in ("&&", "||"):
                self.expr(inner[0]); self.emit("BOOL"); self.emit("DUP")
                jump = self.emit("JZ" if op == "&&" else "JNZ")
                self.emit("POP"); self.expr(inner[1]); self.emit("BOOL"); self.patch(jump)
            else:
                ops = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "IDIV" if scalar_type(node) == "int" else "DIV", "%": "MOD", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE", "==": "EQ", "!=": "NE"}
                if op not in ops:
                    raise ValueError(f"unsupported binary expression {op}")
                self.expr(inner[0]); self.expr(inner[1]); self.emit(ops[op])
                if scalar_type(node)=='int'and op in ('+','-','*','/','%'):self.emit('TRUNC')
        elif kind == "UnaryOperator" and node["opcode"] in ("+", "-", "!"):
            self.expr(inner[0])
            if node["opcode"] != "+": self.emit("NEG" if node["opcode"] == "-" else "NOT")
            if node['opcode']=='-'and scalar_type(node)=='int':self.emit('TRUNC')
        elif kind == "ConditionalOperator":
            self.expr(inner[0]); false = self.emit("JZ"); self.expr(inner[1]); end = self.emit("JUMP"); self.patch(false); self.expr(inner[2]); self.patch(end)
        elif kind in ("CStyleCastExpr", "ImplicitCastExpr"):
            self.expr(inner[0])
            if scalar_type(node) == "int": self.emit("TRUNC")
        elif kind == "CallExpr":
            # Return conversions are part of the call's semantics. In
            # particular, unwrapping a float-returning helper would erase the
            # binary32 rounding before its result is promoted back to double.
            scalar_type(node)
            if unwrap(inner[0]).get("referencedDecl", {}).get("id") in self.definitions:
                if self.helper_requires_slots(node):
                    self.emit_helper_slots(node)
                    return
                with self.inline_helper(node) as expression: self.expr(expression)
                return
            callee = unwrap(inner[0]).get("referencedDecl", {}).get("name")
            builtins = {"sqrt": (1, "SQRT"), "fabs": (1, "ABS"), "fmin": (2, "MIN"), "fmax": (2, "MAX"), "fma": (3, "FMA")}
            if callee not in builtins or len(inner) - 1 != builtins[callee][0]:
                raise ValueError(f"unsupported call {callee!r}; helper functions require explicit inlining")
            if scalar_type(node)!='double' or any(scalar_type(argument)!='double' for argument in inner[1:]):
                raise ValueError('math builtin signature must use double arguments and return double')
            for argument in inner[1:]: self.expr(argument)
            self.emit(builtins[callee][1])
        else:
            raise ValueError(f"unsupported expression {kind}; no metadata was generated")

    def safe_integer_selector(self,node,definition):
        """Narrow no-trap helper: compare two int values and return one.

        Parameter expressions still belong to the full native operation proof.
        Never hide a conversion, local initializer, unused argument or arithmetic
        inside a helper merely because its returned value resembles min/max.
        """
        parameters=[child for child in definition['inner']if child.get('kind')=='ParmVarDecl']
        if len(parameters)!=2 or scalar_type(node)!='int' or any(scalar_type(p)!='int'for p in parameters):return False
        if any(scalar_type(unwrap(argument))!='int'for argument in node['inner'][1:]):return False
        body=next(child for child in definition['inner']if child.get('kind')=='CompoundStmt')
        content=body.get('inner',[])
        if len(content)!=1 or content[0].get('kind')!='ReturnStmt':return False
        expression=unwrap(content[0]['inner'][0])
        if expression.get('kind')!='ConditionalOperator' or len(expression.get('inner',[]))!=3:return False
        condition,left,right=expression['inner'];condition=unwrap(condition)
        if condition.get('kind')!='BinaryOperator' or condition.get('opcode')not in('<','<=','>','>=','==','!='):return False
        def direct_parameter(value):
            value=unwrap(value)
            return value.get('referencedDecl',{}).get('id')if value.get('kind')=='DeclRefExpr'else None
        identifiers={p['id']for p in parameters}
        return {direct_parameter(left),direct_parameter(right)}==identifiers and {direct_parameter(value)for value in condition['inner']}==identifiers

    def helper_requires_slots(self,node):
        key=unwrap(node['inner'][0])['referencedDecl']['id'];definition=self.definitions[key]
        body=next(child for child in definition['inner']if child.get('kind')=='CompoundStmt')
        declarations=[child for child in definition['inner']if child.get('kind')=='ParmVarDecl']+[child for child in walk(body)if child.get('kind')=='VarDecl']
        references=Counter(child.get('referencedDecl',{}).get('id')for child in walk(body)if child.get('kind')=='DeclRefExpr')
        # Symbolic substitution alone loses evaluation of unused arguments or
        # locals, and integer parameter/local conversions can trap in our VM.
        # The current native proof does not establish those evaluations safe.
        safe_selector=self.safe_integer_selector(node,definition)
        if any(references[declaration['id']]==0 or (scalar_type(declaration)=='int'and not safe_selector) for declaration in declarations):
            self.native_helpers_safe=False
        # All initializers and arguments must run once even when their values
        # are unused. Repeated locals would otherwise grow an exponential tree.
        if any(references[declaration['id']]!=1 for declaration in declarations):return True
        return any(child.get('kind')=='CallExpr' and unwrap(child['inner'][0]).get('referencedDecl',{}).get('id')in self.definitions for argument in node['inner'][1:]for child in walk(argument))

    def emit_helper_slots(self,node):
        key=unwrap(node['inner'][0])['referencedDecl']['id'];definition=self.definitions[key]
        key=definition['id']
        parameters=[child for child in definition['inner']if child.get('kind')=='ParmVarDecl']
        body=next(child for child in definition['inner']if child.get('kind')=='CompoundStmt');statements=body.get('inner',[])
        # Apply the same fail-closed SSA validation as compact substitution.
        with self.inline_helper(node):pass
        # Arguments are evaluated before the body's recursion scope and before
        # writing parameter slots, so nested same-helper calls cannot overwrite
        # an outer argument that is still being evaluated.
        for argument in node['inner'][1:]:self.expr(argument)
        previous=self.bindings.copy()
        for declaration in parameters+[child for child in walk(body)if child.get('kind')=='VarDecl']:
            self.bindings.pop(declaration['id'],None)
        try:
            for parameter in reversed(parameters):
                slot=self.declare(parameter)
                if self.types[parameter['id']]=='int':self.emit('TRUNC')
                self.emit('STORE',slot)
            self.call_stack.append(key)
            for statement in statements[:-1]:self.stmt(statement)
            self.expr(statements[-1]['inner'][0])
        finally:
            if self.call_stack and self.call_stack[-1]==key:self.call_stack.pop()
            self.bindings=previous

    def assignment(self, target, value, op="="):
        target = unwrap(target)
        if target.get("kind") == "DeclRefExpr":
            key = target["referencedDecl"]["id"]
            if key not in self.slots: raise ValueError("assignment to non-scalar or unknown local")
            slot = self.slots[key]
            if op != "=": self.emit("LOAD", slot)
            self.expr(value)
            if op != "=": self.emit({"+=": "ADD", "-=": "SUB", "*=": "MUL", "/=": "IDIV" if self.types[key] == "int" else "DIV"}[op])
            if self.types[key] == "int": self.emit("TRUNC")
            self.emit("STORE", slot)
        elif target.get("kind") == "ArraySubscriptExpr":
            array, index = self.access(target, "write")
            if array != 1: raise ValueError("input array must be immutable")
            self.expr(index)
            if op != "=": self.emit("DUP"); self.emit("READ", array)
            self.expr(value)
            if op != "=": self.emit({"+=": "ADD", "-=": "SUB", "*=": "MUL", "/=": "DIV"}[op])
            self.emit("WRITE", array)
        else:
            raise ValueError("unsupported assignment target")

    def stmt(self, node):
        kind = node.get("kind")
        inner = node.get("inner", [])
        if not kind or kind == "NullStmt": return
        if kind == "CompoundStmt":
            for child in inner: self.stmt(child)
        elif kind == "DeclStmt":
            for decl in inner:
                if decl.get("kind") != "VarDecl": raise ValueError("unsupported declaration")
                slot = self.declare(decl)
                if decl.get("inner"):
                    self.expr(decl["inner"][-1])
                    if self.types[decl["id"]] == "int": self.emit("TRUNC")
                    self.emit("STORE", slot)
                else: self.emit("UNINIT", slot)
        elif kind == "ForStmt":
            if len(inner) != 5 or inner[1]: raise ValueError("unsupported for statement")
            init, _, condition, increment, body = inner
            self.stmt(init)
            loop_id = len(self.loops)
            self.loops.append({"id": loop_id, "kind": "for", "condition": self.symbol(condition) if condition else ["constant", 1], "increment": self.symbol(increment) if increment else None, "parent": self.loop_stack[-1] if self.loop_stack else None})
            self.loop_stack.append(loop_id); start = len(self.code)
            if condition: self.expr(condition)
            else: self.emit("CONST", 1)
            end = self.emit("JZ")
            self.stmt(body); self.stmt(increment); self.emit("JUMP", start); self.patch(end); self.loop_stack.pop()
        elif kind == "WhileStmt":
            if len(inner) != 2: raise ValueError("unsupported while statement")
            loop_id = len(self.loops); self.loops.append({"id": loop_id, "kind": "while", "condition": self.symbol(inner[0]), "parent": self.loop_stack[-1] if self.loop_stack else None})
            self.loop_stack.append(loop_id); start = len(self.code); self.expr(inner[0]); end = self.emit("JZ"); self.stmt(inner[1]); self.emit("JUMP", start); self.patch(end); self.loop_stack.pop()
        elif kind == "IfStmt":
            if len(inner) not in (2, 3): raise ValueError("unsupported if declaration")
            self.expr(inner[0]); false = self.emit("JZ"); self.stmt(inner[1])
            if len(inner) == 3:
                end = self.emit("JUMP"); self.patch(false); self.stmt(inner[2]); self.patch(end)
            else: self.patch(false)
        elif kind == "ReturnStmt":
            if inner: self.expr(inner[0])
            else: self.emit("CONST", 0)
            self.emit("RETURN")
        elif kind in ("BinaryOperator", "CompoundAssignOperator") and node.get("opcode") in ("=", "+=", "-=", "*=", "/="):
            self.assignment(inner[0], inner[1], node["opcode"])
        elif kind == "UnaryOperator" and node.get("opcode") in ("++", "--"):
            literal = {"kind": "IntegerLiteral", "value": "1", "type": {"qualType": "int"}}
            self.assignment(inner[0], literal, "+=" if node["opcode"] == "++" else "-=")
        else:
            raise ValueError(f"unsupported statement {kind}; no metadata was generated")

    def compile(self):
        body = next(c for c in self.function["inner"] if c.get("kind") == "CompoundStmt")
        self.stmt(body); self.emit("CONST", 0); self.emit("RETURN")
        if not self.native_helpers_safe:return
        from semantic_cholesky import proven_scalar_cholesky
        if proven_scalar_cholesky(self, body): self.optimized = "scalar_cholesky_column_dag"
        from semantic_cholesky import proven_rightlooking_cholesky
        rightlooking = proven_rightlooking_cholesky(self, body)
        if rightlooking: self.optimized = rightlooking
