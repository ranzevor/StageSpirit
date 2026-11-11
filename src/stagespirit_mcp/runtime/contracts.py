from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    current_data_generation: str = Field(min_length=1)


class Error(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool
    operation_id: str | None = None
    field: str | None = None
    action: str | None = None
    context: ErrorContext | None = None


OperationState = Literal["running", "completed", "failed"]


class OperationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str = Field(min_length=1)
    data_generation: str = Field(min_length=1)
    state: OperationState
    error: Error | None = None


class RecoveryState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["idle", "running", "resolved"] = "idle"


class OperationDetail(OperationReceipt):
    execution_generation: int = Field(ge=1)
    effect_state: Literal["none", "confirmed"]
    recovery: RecoveryState
