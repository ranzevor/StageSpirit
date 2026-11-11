from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from stagespirit_mcp.runtime.configuration import LogLevel
from stagespirit_mcp.runtime.contracts import Error

Revision = Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]
DataGeneration = Annotated[str, Field(min_length=1)]
IdempotencyKey = Annotated[str, Field(min_length=1, max_length=128)]
SectionName = Annotated[str, Field(min_length=1, max_length=64)]
ScopeId = Annotated[str, Field(min_length=1, max_length=128)]


class RuntimeSettingsChanges(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, json_schema_extra={"minProperties": 1}
    )

    log_level: LogLevel = "WARNING"

    @model_validator(mode="after")
    def require_change(self) -> "RuntimeSettingsChanges":
        if not self.model_fields_set:
            raise ValueError("changes 至少需要一个字段。")
        return self


class SettingsGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    section: SectionName
    scope_id: ScopeId | None = None


class SettingsSaveRequest(SettingsGetRequest):
    data_generation: DataGeneration
    expected_revision: Revision
    changes: RuntimeSettingsChanges


class SettingsApplyRequest(SettingsGetRequest):
    data_generation: DataGeneration
    revision: Revision
    idempotency_key: IdempotencyKey


class OperationGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    operation_id: str = Field(min_length=1, max_length=128)


class ConfigurationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section: str = Field(min_length=1)
    scope_id: str | None = None
    data_generation: DataGeneration
    saved_revision: int = Field(ge=0)
    active_revision: int | None = Field(ge=0)
    application_state: Literal["applied", "applying", "failed"]
    apply_operation_id: str = Field(min_length=1)
    error: Error | None = None


class ConfigurationSection[ValuesT: BaseModel](ConfigurationReceipt):
    values: ValuesT
    active_values: ValuesT | None
