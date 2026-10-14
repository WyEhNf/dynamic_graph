"""Record the installed active dependency closure without changing packages."""
import importlib.metadata as metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def main():
    roots = ["transformers", "tokenizers", "huggingface-hub", "safetensors",
             "regex", "truststore", "requests", "setuptools", "torch",
             "bitsandbytes", "accelerate"]
    pending = list(roots)
    packages = {}
    missing = []
    environment = default_environment()
    environment["extra"] = ""
    while pending:
        name = canonicalize_name(pending.pop())
        if name in packages or name in missing:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        dependencies = []
        for text in distribution.requires or []:
            requirement = Requirement(text)
            if requirement.marker is None or requirement.marker.evaluate(environment):
                dependencies.append(canonicalize_name(requirement.name))
        packages[name] = {"name": distribution.metadata["Name"],
                          "version": distribution.version,
                          "active_dependencies": sorted(set(dependencies))}
        pending.extend(dependencies)
    report = {"scope": "Installed active dependency closure, not a portable CUDA installer lock",
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "executable": sys.executable,
              "platform": platform.platform(), "roots": roots,
              "packages": dict(sorted(packages.items())), "missing": sorted(missing)}
    output = Path(__file__).resolve().parents[1] / "artifacts/model-environment-inventory.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packages": len(packages), "missing": missing, "output": str(output)}))


if __name__ == "__main__":
    main()
