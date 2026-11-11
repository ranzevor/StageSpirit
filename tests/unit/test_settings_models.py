import pytest
from pydantic import ValidationError

from stagespirit_mcp.modules.settings.models import (
    RuntimeSettingsChanges,
    SettingsApplyRequest,
    SettingsSaveRequest,
)
from stagespirit_mcp.runtime.configuration import RuntimeSettings


@pytest.mark.parametrize(
    "changes",
    [{}, {"log_level": None}, {"log_level": "debug"}, {"log_level": True}, {"unknown": "ERROR"}],
)
def test_runtime_changes_reject_invalid_or_empty_values(changes: dict) -> None:
    with pytest.raises(ValidationError):
        RuntimeSettingsChanges.model_validate(changes)


@pytest.mark.parametrize("revision", [True, False, -1, 1.0, "1", 9223372036854775808])
def test_revision_requires_bounded_integer(revision: object) -> None:
    with pytest.raises(ValidationError):
        SettingsSaveRequest.model_validate(
            {
                "section": "runtime",
                "data_generation": "generation",
                "expected_revision": revision,
                "changes": {"log_level": "ERROR"},
            }
        )


def test_runtime_changes_are_typed_and_immutable() -> None:
    patch = RuntimeSettingsChanges.model_validate({"log_level": "ERROR"})
    assert patch.model_dump(exclude_unset=True) == {"log_level": "ERROR"}
    assert RuntimeSettings().log_level == "WARNING"
    with pytest.raises(ValidationError):
        patch.log_level = "INFO"


@pytest.mark.parametrize("key", ["", "x" * 129, None, 1])
def test_apply_requires_bounded_operation_key(key: object) -> None:
    with pytest.raises(ValidationError):
        SettingsApplyRequest.model_validate(
            {
                "section": "runtime",
                "data_generation": "generation",
                "revision": 0,
                "idempotency_key": key,
            }
        )
