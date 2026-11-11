from typing import Protocol

from pydantic import BaseModel


class ConfigurationParticipant(Protocol):
    section: str
    scope_id: str | None

    def defaults(self) -> dict[str, object]: ...

    def prepare(self, values: dict[str, object]) -> BaseModel: ...

    def snapshot(self) -> BaseModel | None: ...

    def activate(self, candidate: BaseModel | None) -> None:
        """Atomically publish an in-memory snapshot; failure retains the previous snapshot."""
        ...
