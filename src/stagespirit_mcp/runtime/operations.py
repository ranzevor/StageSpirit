import sqlite3
from uuid import uuid4

from stagespirit_mcp.runtime.contracts import (
    Error,
    OperationDetail,
    OperationReceipt,
    RecoveryState,
)
from stagespirit_mcp.runtime.errors import BusinessError


def create_operation(
    connection: sqlite3.Connection,
    *,
    data_generation: str,
    tool: str,
    section: str,
    scope_id: str,
    revision: int,
    idempotency_key: str | None = None,
) -> str:
    operation_id = str(uuid4())
    connection.execute(
        """INSERT INTO runtime_operations
            (operation_id, data_generation, tool, section, scope_id, revision,
             idempotency_key, execution_generation, state, recovery_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'running', 'idle')""",
        (operation_id, data_generation, tool, section, scope_id, revision, idempotency_key),
    )
    return operation_id


def finish_operation(
    connection: sqlite3.Connection,
    operation_id: str,
    error: Error | None = None,
    *,
    execution_generation: int | None = None,
) -> None:
    connection.execute(
        """UPDATE runtime_operations SET state = ?, error_json = ?,
            recovery_state = CASE WHEN recovery_state = 'running' THEN 'resolved'
                ELSE recovery_state END
            WHERE operation_id = ? AND state = 'running'
            AND (? IS NULL OR execution_generation = ?)""",
        (
            "failed" if error else "completed",
            error.model_dump_json(exclude_none=True) if error else None,
            operation_id,
            execution_generation,
            execution_generation,
        ),
    )


def get_operation(connection: sqlite3.Connection, operation_id: str) -> OperationDetail:
    row = connection.execute(
        "SELECT * FROM runtime_operations WHERE operation_id = ?", (operation_id,)
    ).fetchone()
    if row is None:
        raise BusinessError(
            Error(
                code="NOT_FOUND",
                message="当前运行配置中没有这个操作。",
                retryable=False,
                field="operation_id",
            )
        )
    return OperationDetail(
        operation_id=row["operation_id"],
        data_generation=row["data_generation"],
        state=row["state"],
        execution_generation=row["execution_generation"],
        effect_state="confirmed" if row["state"] == "completed" else "none",
        recovery=RecoveryState(state=row["recovery_state"]),
        error=Error.model_validate_json(row["error_json"]) if row["error_json"] else None,
    )


def operation_receipt(detail: OperationDetail) -> OperationReceipt:
    return OperationReceipt(
        operation_id=detail.operation_id,
        data_generation=detail.data_generation,
        state=detail.state,
        error=detail.error,
    )
