import re
from pathlib import Path

from platformdirs import user_data_path

_RESERVED_NAMES = {"con", "prn", "aux", "nul"} | {
    f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
}


def profile_directory(data_root: Path | None, profile_id: str) -> Path:
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", profile_id) is None:
        raise ValueError(
            "运行配置 ID 需使用 1 至 64 个小写字母、数字、连字符或下划线，并以字母或数字开头。"
        )
    if profile_id in _RESERVED_NAMES:
        raise ValueError("运行配置 ID 使用了系统保留名称。")
    root = data_root if data_root is not None else user_data_path("StageSpirit", appauthor=False)
    return root.expanduser().resolve() / "profiles" / profile_id
