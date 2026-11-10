import sys
from pathlib import Path

import pytest
from mcp import StdioServerParameters


@pytest.fixture
def server_parameters(tmp_path: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "stagespirit_mcp",
            "serve",
            "--data-dir",
            str(tmp_path / "中文 数据"),
        ],
        cwd=tmp_path,
        env={"PYTHONIOENCODING": "gbk", "PYTHONUTF8": "0"},
    )
