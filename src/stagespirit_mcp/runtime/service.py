import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from stagespirit_mcp import __version__
from stagespirit_mcp.runtime.models import ModuleSummary, RuntimeSummary


@dataclass(frozen=True)
class RuntimeInstance:
    profile_id: str
    data_generation: str
    instance_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _started_monotonic: float = field(default_factory=monotonic, repr=False)

    def snapshot(self) -> RuntimeSummary:
        return RuntimeSummary(
            profile_id=self.profile_id,
            data_generation=self.data_generation,
            instance_id=self.instance_id,
            version=__version__,
            state="running",
            process_id=os.getpid(),
            started_at=self.started_at,
            uptime_ms=max(0, int((monotonic() - self._started_monotonic) * 1000)),
            capability_groups=["core"],
            modules=[ModuleSummary(name="runtime", state="ready")],
        )
