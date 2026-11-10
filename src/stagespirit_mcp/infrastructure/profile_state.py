import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from pydantic import ValidationError

from stagespirit_mcp.runtime.errors import StartupError
from stagespirit_mcp.runtime.models import ControlState


def load_control_state(directory: Path, profile_id: str) -> ControlState:
    path = directory / "control.json"
    if path.exists():
        try:
            state = ControlState.model_validate_json(path.read_bytes())
        except (ValidationError, UnicodeError) as error:
            raise StartupError("运行配置的维护状态无法由当前版本读取。") from error
        if state.profile_id != profile_id:
            raise StartupError("运行配置目录与维护状态中的配置身份不一致。")
        return state

    state = ControlState(profile_id=profile_id, data_generation=str(uuid4()))
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".control-",
            suffix=".tmp",
            dir=directory,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(state.model_dump_json(indent=2) + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return state
