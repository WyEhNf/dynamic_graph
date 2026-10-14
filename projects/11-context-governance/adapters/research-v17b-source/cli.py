import argparse
import json
from pathlib import Path
from .core import Item, govern


def main():
    parser = argparse.ArgumentParser(description="Govern context; demo budget is UTF-8 bytes, not model tokens")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = govern(data["task"], [Item(**x) for x in data["items"]], data["budget"],
                    dependencies=data.get('dependencies'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["metrics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
