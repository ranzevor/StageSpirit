"""Export the schemas implemented by the runtime models."""

import argparse
import json
import sys
from pathlib import Path

from stagespirit_mcp.runtime.models import RuntimeSummary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **RuntimeSummary.model_json_schema(),
    }
    content = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    target = Path(__file__).resolve().parents[1] / "contracts/schemas/runtime-summary.schema.json"
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != content:
            print(
                "运行状态契约需要重新生成，请运行 uv run python scripts/export_contracts.py。",
                file=sys.stderr,
            )
            return 1
        return 0
    target.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
