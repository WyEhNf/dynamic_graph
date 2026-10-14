"""Small, fail-closed structural proof of the scalar Cholesky dependence graph.

This recognizes typed loop/operation semantics, not C source spelling. The generic
AST VM remains authoritative for all programs outside this provable subset.
"""
from c_frontend import unwrap,integer_expression

def _check(condition):
    if not condition:
        raise ValueError('unproven operation graph')

def statements(node):
    while node.get('kind') == 'CompoundStmt' and len(node.get('inner', [])) == 1:
        node = node['inner'][0]
    return node.get('inner', []) if node.get('kind') == 'CompoundStmt' else [node]

def normalized_counted_loops(node):
    """Expose a DeclStmt + bottom-increment WhileStmt as a ForStmt to proof.

    Actual bytecode is never rewritten. The remaining complete proof must
    establish the initializer, bound, unit step and entire operation body; no
    loop is accepted merely because it has the surface shape of a counted loop.
    """
    children=[normalized_counted_loops(child) for child in node.get('inner',[])]
    result={**node}
    if 'inner' in node:result['inner']=children
    if node.get('kind')!='CompoundStmt':return result
    converted=[];index=0
    while index<len(children):
        declaration=children[index]
        if index+1<len(children) and declaration.get('kind')=='DeclStmt' and len(declaration.get('inner',[]))==1:
            loop=children[index+1]
            if loop.get('kind')=='WhileStmt' and len(loop.get('inner',[]))==2:
                condition,body=loop['inner'];content=statements(body)
                if content:
                    increment=content[-1]
                    if increment.get('kind') in ('UnaryOperator','BinaryOperator','CompoundAssignOperator'):
                        converted.append({'kind':'ForStmt','inner':[declaration,{},condition,increment,{'kind':'CompoundStmt','inner':content[:-1]}]});index+=2;continue
        converted.append(declaration);index+=1
    result['inner']=converted
    return result

def proven_scalar_cholesky(compiler, body):
    try:
        top = statements(normalized_counted_loops(body))
        if len(top) == 2:
            _check(top[1]['kind'] == 'ReturnStmt' and compiler.symbol(top[1]['inner'][0]) == ['constant', 0])
        else:
            _check(len(top) == 1 and compiler.function['type']['qualType'].startswith('void ('))
        n = ['slot', compiler.shape_slot]
        zero = ['constant', 0]
        one = ['constant', 1]

        def loop(node, limit, inclusive=False):
            _check(node['kind'] == 'ForStmt')
            init, empty, condition, increment, content = node['inner']
            _check(not empty and init['kind'] == 'DeclStmt' and (len(init['inner']) == 1))
            var = init['inner'][0]
            _check(compiler.types[var['id']] == 'int' and compiler.symbol(var['inner'][0]) == zero)
            symbol = ['slot', compiler.slots[var['id']]]
            cond = compiler.symbol(condition)
            valid = [['<=' if inclusive else '<', symbol, limit]]
            valid += [['<', symbol, integer_expression('+',limit,one)]] if inclusive else [['<=', symbol, ['-', limit, one]]]
            _check(cond in valid)
            inc = compiler.symbol(increment)
            _check(inc in [['++', symbol], ['+=', symbol, one], ['=', symbol, integer_expression('+',symbol,one)]])
            return (symbol, content)
        i, row_body = loop(top[0], n)
        row_statements = statements(row_body)
        _check(len(row_statements) == 1)
        j, entry_body = loop(row_statements[0], i, True)
        entries = statements(entry_body)
        _check(len(entries) == 3)
        declaration, reduction, branch = entries
        _check(declaration['kind'] == 'DeclStmt' and len(declaration['inner']) == 1)
        accum = declaration['inner'][0]
        _check(compiler.types[accum['id']] == 'double' and compiler.symbol(accum['inner'][0]) == zero)
        s = ['slot', compiler.slots[accum['id']]]
        k, reduction_body = loop(reduction, j)

        def index(row, col):
            return integer_expression('+',integer_expression('*',row,n),col)

        def read(array, row, col):
            return ['read', array, index(row, col)]
        terms = ['*', read(1, i, k), read(1, j, k)]
        ops = statements(reduction_body)
        _check(len(ops) == 1)
        _check(compiler.symbol(ops[0]) in [['+=', s, terms], ['=', s, ['+', s, terms]]])
        _check(branch['kind'] == 'IfStmt' and len(branch['inner']) == 3)
        condition, diagonal, offdiagonal = branch['inner']
        _check(compiler.symbol(condition) in [['==', i, j], ['==', j, i]])
        ds, os = (statements(diagonal), statements(offdiagonal))
        _check(len(ds) == len(os) == 1)
        target = read(1, i, j)
        _check(compiler.symbol(ds[0]) == ['=', target, ['call', 'sqrt', ['-', read(0, i, i), s]]])
        _check(compiler.symbol(os[0]) == ['=', target, ['/', ['-', read(0, i, j), s], read(1, j, j)]])
        return True
    except (AssertionError, KeyError, IndexError, ValueError):
        return False

def proven_rightlooking_cholesky(compiler, body):
    """Prove the official image's operation DAG, with optional exact tile wrappers.

    Tile-loop proof uses positive block-size, contiguous [start,min(start+B,end))
    ranges and B increments. It is symbolic; it does not sample N to infer safety.
    All floating operations and their order within an updated element are checked.
    """
    try:
        top = statements(normalized_counted_loops(body))
        if len(top) == 2:
            _check(top[1]['kind'] == 'ReturnStmt' and compiler.symbol(top[1]['inner'][0]) == ['constant', 0])
        else:
            _check(len(top) == 1 and compiler.function['type']['qualType'].startswith('void ('))
        zero, one = (['constant', 0], ['constant', 1])
        n = ['slot', compiler.shape_slot]
        block = ['slot', compiler.block_slot]

        def components(node):
            _check(node['kind'] == 'ForStmt')
            init, empty, condition, increment, content = node['inner']
            _check(not empty and init['kind'] == 'DeclStmt' and (len(init['inner']) == 1))
            declaration = init['inner'][0]
            _check(compiler.types[declaration['id']] == 'int')
            variable = ['slot', compiler.slots[declaration['id']]]
            return (variable, compiler.symbol(declaration['inner'][0]), compiler.symbol(condition), compiler.symbol(increment), content)

        def unit_increment(variable, increment):
            return increment in [['++', variable], ['+=', variable, one], ['=', variable, integer_expression('+',variable,one)]]

        def loop(node, lower, limit, inclusive=False):
            variable, initial, condition, increment, content = components(node)
            _check(initial == lower)
            valid=[['<=' if inclusive else '<',variable,limit]]
            valid += [['<',variable,integer_expression('+',limit,one)]] if inclusive else [['<=',variable,['-',limit,one]]]
            _check(condition in valid)
            if unit_increment(variable, increment):
                return (variable, content)
            _check(compiler.block_slot >= 0)
            _check(increment in [['+=', variable, block], ['=', variable, integer_expression('+',variable,block)]])
            children = statements(content)
            _check(len(children) == 2)
            end_declaration, inner_loop = children
            _check(end_declaration['kind'] == 'DeclStmt' and len(end_declaration['inner']) == 1)
            end = end_declaration['inner'][0]
            end_slot = ['slot', compiler.slots[end['id']]]
            bound = integer_expression('+',limit,one) if inclusive else limit
            plus_block = integer_expression('+',variable,block)
            _check(compiler.symbol(end['inner'][0]) == ['select', ['<', plus_block, bound], plus_block, bound])
            inner_variable, inner_initial, inner_condition, inner_increment, inner_content = components(inner_loop)
            _check(inner_initial == variable and inner_condition == ['<', inner_variable, end_slot])
            _check(unit_increment(inner_variable, inner_increment))
            return (inner_variable, inner_content)
        i, column_body = loop(top[0], zero, n)
        column_statements = statements(column_body)
        _check(len(column_statements) == 2)
        diagonal, row_loop = column_statements

        def index(row, col):
            return integer_expression('+',integer_expression('*',row,n),col)

        def read(array, row, col):
            return ['read', array, index(row, col)]
        _check(compiler.symbol(diagonal) == ['=', read(1, i, i), ['call', 'sqrt', ['-', read(0, i, i), read(1, i, i)]]])
        j, row_body = loop(row_loop, integer_expression('+',i,one), n)
        row_statements = statements(row_body)
        _check(len(row_statements) == 2)
        division, update_loop = row_statements
        _check(compiler.symbol(division) == ['=', read(1, j, i), ['/', ['-', read(0, j, i), read(1, j, i)], read(1, i, i)]])
        k, update_body = loop(update_loop, integer_expression('+',i,one), j, True)
        updates = statements(update_body)
        _check(len(updates) == 1)
        update = compiler.symbol(updates[0])
        left, right, accumulator = (read(1, j, i), read(1, k, i), read(1, j, k))
        if update == ['=', accumulator, ['+', ['*', left, right], accumulator]]:
            return 'rightlooking_cholesky_column_dag'
        if update == ['=', accumulator, ['call', 'fma', left, right, accumulator]]:
            return 'rightlooking_cholesky_column_dag_fma'
        return None
    except (AssertionError, KeyError, IndexError, ValueError):
        return None
