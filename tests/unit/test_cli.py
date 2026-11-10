import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("arguments", [["--version"], ["--help"], ["serve", "--help"]])
def test_cli_information_does_not_load_runtime(arguments: list[str], tmp_path: Path) -> None:
    script = (
        "import sys; sys.modules['mcp'] = None; sys.modules['filelock'] = None; "
        "from stagespirit_mcp.entrypoints.cli import main; "
        "raise SystemExit(main(sys.argv[1:]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, *arguments],
        cwd=tmp_path,
        env=os.environ.copy(),
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0
    assert result.stdout
    assert result.stderr == b""
    assert not list(tmp_path.iterdir())
