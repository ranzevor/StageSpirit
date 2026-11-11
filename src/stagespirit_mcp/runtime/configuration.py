import logging
from threading import RLock
from typing import Literal

from pydantic import BaseModel, ConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class RuntimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    log_level: LogLevel = "WARNING"


class RuntimeConfiguration:
    section = "runtime"
    scope_id: str | None = None

    def __init__(self) -> None:
        self._lock = RLock()
        self._active: RuntimeSettings | None = None
        self._loggers = (logging.getLogger("stagespirit"), logging.getLogger("mcp"))
        self._previous_levels = tuple(logger.level for logger in self._loggers)

    def prepare(self, values: dict[str, object]) -> RuntimeSettings:
        return RuntimeSettings.model_validate(values)

    def defaults(self) -> dict[str, object]:
        return RuntimeSettings().model_dump()

    def snapshot(self) -> RuntimeSettings | None:
        with self._lock:
            return self._active

    def activate(self, candidate: BaseModel | None) -> None:
        if candidate is not None and not isinstance(candidate, RuntimeSettings):
            raise TypeError("运行配置类型不匹配。")
        with self._lock:
            if candidate is None:
                for logger, level in zip(self._loggers, self._previous_levels, strict=True):
                    logger.setLevel(level)
            else:
                for logger in self._loggers:
                    logger.setLevel(candidate.log_level)
            self._active = candidate

    def close(self) -> None:
        self.activate(None)
