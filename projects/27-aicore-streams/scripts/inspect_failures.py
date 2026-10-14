"""Read-only diagnostics: candidate serial peaks on reproducible failed graphs."""
import argparse
import json
from generate_cases import serial_witness


def dfs_order(nodes, mode):
    index = {x["id"]: x for x in nodes}
    seen = set()
    order = []
    roots = list(index)
    roots.sort(key=lambda i: (index[i]["output_memory"], index[i]["workspace_memory"]), reverse=bool(mode & 1))
    for root in roots:
        stack = [(root, False)]
        while stack:
            identity, exit = stack.pop()
            if exit:
                order.append(index[identity])
            elif identity not in seen:
                seen.add(identity)
                stack.append((identity, True))
                inputs = sorted(index[identity]["inputs"], key=lambda p: index[p]["output_memory"], reverse=bool(mode & 2))
                stack.extend((p, False) for p in inputs)
    return order


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    args = p.parse_args()
    for x in json.load(open(args.input))["cases"]:
        print(x["name"], "limit", x["hardware"]["memory_limit"], "dfs_peaks", [serial_witness(dfs_order(x["nodes"], m))[2] for m in range(4)])


if __name__ == "__main__":
    main()
