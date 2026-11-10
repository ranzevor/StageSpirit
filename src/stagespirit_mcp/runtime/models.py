from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ControlState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    format_version: int = Field(default=1, ge=1, le=1)
    profile_id: str = Field(min_length=1)
    data_generation: str = Field(min_length=1)


class ModuleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    state: Literal["ready"]


class RuntimeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str = Field(min_length=1, description="当前运行配置")
    data_generation: str = Field(min_length=1, description="持久数据集的代际身份")
    instance_id: str = Field(min_length=1, description="本次服务进程的运行实例")
    version: str = Field(min_length=1, description="已安装的 StageSpirit 版本")
    state: Literal["running"]
    process_id: int = Field(gt=0)
    started_at: datetime
    uptime_ms: int = Field(ge=0)
    capability_groups: list[Literal["core"]]
    modules: list[ModuleSummary]
