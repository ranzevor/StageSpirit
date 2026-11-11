"""Export schemas implemented by the current runtime and configuration models."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from stagespirit_mcp.modules.settings.models import (
    ConfigurationSection,
    OperationGetRequest,
    SettingsApplyRequest,
    SettingsGetRequest,
    SettingsSaveRequest,
)
from stagespirit_mcp.runtime.configuration import RuntimeSettings
from stagespirit_mcp.runtime.models import RuntimeSummary

MODELS: dict[str, type[BaseModel]] = {
    "runtime-summary": RuntimeSummary,
    "runtime-settings": RuntimeSettings,
    "settings-section": ConfigurationSection[RuntimeSettings],
    "settings-get-request": SettingsGetRequest,
    "settings-save-request": SettingsSaveRequest,
    "settings-apply-request": SettingsApplyRequest,
    "operation-get-request": OperationGetRequest,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "contracts/schemas"
    outdated: list[str] = []
    for name, model in MODELS.items():
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **model.model_json_schema(),
        }
        content = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
        target = root / f"{name}.schema.json"
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != content:
                outdated.append(name)
        else:
            target.write_text(content, encoding="utf-8", newline="\n")
    if outdated:
        print(
            "契约需要重新生成："
            + "、".join(outdated)
            + "。请运行 uv run python scripts/export_contracts.py。",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
