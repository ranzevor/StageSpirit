import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from stagespirit_mcp.bootstrap.application import open_runtime
from stagespirit_mcp.infrastructure import profile_state
from stagespirit_mcp.runtime.errors import StartupError


def test_generation_survives_restart_and_profiles_are_isolated(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as first:
        before = first.snapshot()
        with open_runtime("second", tmp_path) as other:
            assert other.data_generation != first.data_generation
    control_path = tmp_path / "profiles/default/control.json"
    original = control_path.read_bytes()
    with open_runtime("default", tmp_path) as second:
        after = second.snapshot()
    assert before.data_generation == after.data_generation
    assert before.instance_id != after.instance_id
    assert before.started_at <= after.started_at
    assert before.uptime_ms >= 0
    assert control_path.read_bytes() == original


def test_active_profile_is_exclusive_and_lock_is_released(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as first:
        with pytest.raises(StartupError, match="活动实例"):
            with open_runtime("default", tmp_path):
                pytest.fail("A second instance acquired the same profile")
    with open_runtime("default", tmp_path) as recovered:
        assert recovered.data_generation == first.data_generation


@pytest.mark.parametrize(
    "content",
    [
        b"not json",
        b"\xff",
        b"{}",
        b'{"format_version":2,"profile_id":"default","data_generation":"generation"}',
        b'{"format_version":true,"profile_id":"default","data_generation":"generation"}',
        b'{"profile_id":"other","data_generation":"generation"}',
        b'{"profile_id":"default","data_generation":""}',
        b'{"profile_id":"default","data_generation":"generation","extra":0}',
    ],
)
def test_invalid_control_state_is_preserved(tmp_path: Path, content: bytes) -> None:
    directory = tmp_path / "profiles/default"
    directory.mkdir(parents=True)
    control_path = directory / "control.json"
    control_path.write_bytes(content)
    with pytest.raises(StartupError):
        with open_runtime("default", tmp_path):
            pytest.fail("Invalid control state was accepted")
    assert control_path.read_bytes() == content
    control_path.write_text(
        json.dumps({"profile_id": "default", "data_generation": "repaired-generation"}),
        encoding="utf-8",
    )
    with open_runtime("default", tmp_path) as runtime:
        assert runtime.data_generation == "repaired-generation"


def test_failed_atomic_write_cleans_up_and_releases_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_replace(*args: object) -> None:
        raise OSError("injected replace failure")

    with monkeypatch.context() as patch:
        patch.setattr(profile_state.os, "replace", fail_replace)
        with pytest.raises(OSError, match="injected replace failure"):
            with open_runtime("default", tmp_path):
                pytest.fail("Failed state write was accepted")
    directory = tmp_path / "profiles/default"
    assert not (directory / "control.json").exists()
    assert not list(directory.glob(".control-*.tmp"))
    with open_runtime("default", tmp_path) as runtime:
        assert runtime.data_generation


def test_process_exit_releases_profile_lock(tmp_path: Path) -> None:
    script = (
        "import os, sys\n"
        "from pathlib import Path\n"
        "from stagespirit_mcp.bootstrap.application import open_runtime\n"
        "with open_runtime('default', Path(sys.argv[1])) as runtime:\n"
        "    print(runtime.data_generation, flush=True)\n"
        "    os._exit(0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        check=True,
        capture_output=True,
        timeout=20,
        env=os.environ.copy(),
    )
    generation = result.stdout.decode("utf-8").strip()
    with open_runtime("default", tmp_path) as runtime:
        assert runtime.data_generation == generation


def test_active_profile_rejects_another_process(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as active:
        result = subprocess.run(
            [sys.executable, "-m", "stagespirit_mcp", "serve", "--data-dir", str(tmp_path)],
            input=b"",
            capture_output=True,
            timeout=20,
            cwd=tmp_path,
        )
        assert result.returncode == 1
        assert result.stdout == b""
        assert "已有活动实例" in result.stderr.decode("utf-8")
        saved = json.loads((tmp_path / "profiles/default/control.json").read_text("utf-8"))
        assert saved["data_generation"] == active.data_generation
