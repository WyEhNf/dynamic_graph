"""Fresh row counts, ordered operands and original topological layouts.

Synthetic heldout inputs, not official application traces. GET/SET names stay
unique and disjoint; each original arithmetic identity is retained once.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path


def generate(seed, rows, columns, bits):
    rng = random.Random(seed)
    nodes = []
    def emit(op, args=(), reg=None):
        index = len(nodes)
        nodes.append((op, tuple(args), reg))
        return index
    weights = [emit('GET', reg=f'w{column}') for column in range(columns)]
    private = [[emit('GET', reg=f'x{row}_{column}') for column in range(columns)] for row in range(rows)]
    reverse_pair = rng.choice((False, True))
    for row in range(rows):
        products = []
        for column in range(columns):
            operands = [weights[column], private[row][column]]
            if rng.random() < .5:
                operands.reverse()
            products.append(emit('MULW', operands))
        pair = products[:2]
        if reverse_pair:
            pair.reverse()
        total = emit('ADD', pair)
        for product in products[2:]:
            operands = [total, product]
            if rng.random() < .5:
                operands.reverse()
            total = emit('ADD', operands)
        emit('SET', (total,), f'out{row}')
    pending = [len(set(args)) for _, args, _ in nodes]
    users = [[] for _ in nodes]
    for index, (_, args, _) in enumerate(nodes):
        for source in set(args):
            users[source].append(index)
    ready = [i for i, count in enumerate(pending) if not count]
    order = []
    while ready:
        position = rng.randrange(len(ready))
        index = ready[position]
        ready[position] = ready[-1]
        ready.pop()
        order.append(index)
        for user in users[index]:
            pending[user] -= 1
            if not pending[user]:
                ready.append(user)
    rank = {index: position for position, index in enumerate(order)}
    output = []
    for position, index in enumerate(order):
        op, args, reg = nodes[index]
        item = {'id': position, 'op': op}
        if args:
            item['inputs'] = [f't#{position - rank[source]}' for source in args]
        if reg is not None:
            item['reg'] = reg
        output.append(item)
    return {'block_id': f'heldout-reduction-{rows}-{columns}-{bits}-{seed}',
            'bit_width': bits, 'instructions': output}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination')
    parser.add_argument('--seed', type=int, default=8050001)
    args = parser.parse_args()
    target = Path(args.destination)
    target.mkdir(exist_ok=False)
    cases = []
    for rows in (2, 3, 4):
        for columns in (2, 7, 31, 113, 331, 631):
            for bits in (2, 3, 4, 5):
                seed = args.seed + len(cases)
                data = generate(seed, rows, columns, bits)
                cases.append({'family': f'age_reduction_rows{rows}', 'target_nodes': len(data['instructions']),
                              'seed': seed, 'input': data})
    corpus = target / 'inputs.jsonl'
    corpus.write_text(''.join(json.dumps(case, separators=(',', ':')) + '\n' for case in cases), encoding='utf-8')
    (target / 'manifest.json').write_text(json.dumps({'count': len(cases), 'seed': args.seed,
        'input_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'synthetic complete original reduction chains; different rows, columns, topological orders and ordered operands; not official'}, indent=2) + '\n')
    print(json.dumps({'path': str(corpus), 'count': len(cases)}))


if __name__ == '__main__':
    main()
