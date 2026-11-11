from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stagespirit_mcp.runtime.contracts import Error


class StartupError(RuntimeError):
    """The selected runtime profile could not be started."""


class BusinessError(Exception):
    def __init__(self, error: "Error") -> None:
        super().__init__(error.message)
        self.error = error
