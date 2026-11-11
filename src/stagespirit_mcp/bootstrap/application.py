from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock, Timeout

from stagespirit_mcp.infrastructure.paths import profile_directory
from stagespirit_mcp.infrastructure.profile_state import load_control_state
from stagespirit_mcp.modules.settings.service import SettingsService
from stagespirit_mcp.runtime.configuration import RuntimeConfiguration
from stagespirit_mcp.runtime.errors import StartupError
from stagespirit_mcp.runtime.service import RuntimeInstance


@contextmanager
def open_runtime(profile_id: str, data_root: Path | None) -> Generator[RuntimeInstance]:
    try:
        directory = profile_directory(data_root, profile_id)
    except ValueError as error:
        raise StartupError(str(error)) from error
    directory.mkdir(parents=True, exist_ok=True)
    lock = FileLock(directory / "instance.lock")
    try:
        lock.acquire(timeout=0)
    except Timeout as error:
        raise StartupError(f"运行配置 {profile_id} 已有活动实例。") from error

    try:
        state = load_control_state(directory, profile_id)
        configuration = RuntimeConfiguration()
        settings = SettingsService(
            directory, state.profile_id, state.data_generation, (configuration,)
        )
        try:
            yield RuntimeInstance(
                profile_id=state.profile_id,
                data_generation=state.data_generation,
                configuration=configuration,
                settings=settings,
            )
        finally:
            settings.close()
    finally:
        lock.release()
