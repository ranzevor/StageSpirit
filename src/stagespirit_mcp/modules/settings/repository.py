import json
import sqlite3
from dataclasses import dataclass

from stagespirit_mcp.infrastructure.storage.database import Database
from stagespirit_mcp.modules.settings.models import ConfigurationReceipt
from stagespirit_mcp.runtime.contracts import Error
from stagespirit_mcp.runtime.errors import BusinessError
from stagespirit_mcp.runtime.operations import create_operation, finish_operation


def revision_conflict() -> BusinessError:
    return BusinessError(
        Error(
            code="REVISION_CONFLICT",
            message="配置修订已改变，请读取当前修订后重新组织变更。",
            retryable=False,
            field="expected_revision",
        )
    )


@dataclass(frozen=True)
class ActivationToken:
    section: str
    scope_id: str
    revision: int
    data_generation: str
    epoch: str
    operation_id: str
    execution_generation: int


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def read(self, section: str, scope_id: str) -> sqlite3.Row:
        row = self.database.connection.execute(
            "SELECT * FROM settings_sections WHERE section = ? AND scope_id = ?",
            (section, scope_id),
        ).fetchone()
        if row is None:
            raise BusinessError(
                Error(
                    code="NOT_FOUND", message="配置分区不存在。", retryable=False, field="section"
                )
            )
        return row

    def begin(
        self,
        *,
        section: str,
        scope_id: str,
        data_generation: str,
        revision: int,
        epoch: str,
        values: dict[str, object] | None = None,
        idempotency_key: str | None = None,
        tool: str,
    ) -> ActivationToken:
        with self.database.transaction() as connection:
            self.database.check_generation(connection, data_generation)
            row = connection.execute(
                "SELECT * FROM settings_sections WHERE section = ? AND scope_id = ?",
                (section, scope_id),
            ).fetchone()
            if row is None or row["saved_revision"] != revision:
                raise revision_conflict()
            if values is not None and revision == 9223372036854775807:
                raise BusinessError(
                    Error(
                        code="RESOURCE_LIMIT",
                        message="配置修订已达到数据库整数上限。",
                        retryable=False,
                    )
                )
            next_revision = revision + 1 if values is not None else revision
            finish_operation(connection, row["apply_operation_id"], revision_conflict().error)
            operation_id = create_operation(
                connection,
                data_generation=data_generation,
                tool=tool,
                section=section,
                scope_id=scope_id,
                revision=next_revision,
                idempotency_key=idempotency_key,
            )
            connection.execute(
                """UPDATE settings_sections SET saved_revision = ?,
                    values_json = ?, application_state = 'applying',
                    apply_operation_id = ?, activation_epoch = ?, error_json = NULL
                    WHERE section = ? AND scope_id = ?""",
                (
                    next_revision,
                    json.dumps(values, ensure_ascii=False)
                    if values is not None
                    else row["values_json"],
                    operation_id,
                    epoch,
                    section,
                    scope_id,
                ),
            )
        return ActivationToken(
            section, scope_id, next_revision, data_generation, epoch, operation_id, 1
        )

    def current(self, connection: sqlite3.Connection, token: ActivationToken) -> bool:
        row = connection.execute(
            """SELECT s.saved_revision, s.activation_epoch, s.apply_operation_id,
                o.execution_generation, o.state, m.data_generation FROM settings_sections s
                JOIN runtime_operations o ON o.operation_id = s.apply_operation_id
                JOIN runtime_metadata m ON m.singleton = 1
                WHERE s.section = ? AND s.scope_id = ?""",
            (token.section, token.scope_id),
        ).fetchone()
        return row is not None and (
            row["saved_revision"],
            row["activation_epoch"],
            row["apply_operation_id"],
            row["execution_generation"],
            row["state"],
            row["data_generation"],
        ) == (
            token.revision,
            token.epoch,
            token.operation_id,
            token.execution_generation,
            "running",
            token.data_generation,
        )

    def complete(
        self, connection: sqlite3.Connection, token: ActivationToken, error: Error | None = None
    ) -> bool:
        if not self.current(connection, token):
            return False
        connection.execute(
            """UPDATE settings_sections SET active_revision = CASE WHEN ? IS NULL
                    THEN saved_revision ELSE active_revision END,
                application_state = ?, error_json = ?
                WHERE section = ? AND scope_id = ?""",
            (
                error.code if error else None,
                "failed" if error else "applied",
                error.model_dump_json(exclude_none=True) if error else None,
                token.section,
                token.scope_id,
            ),
        )
        finish_operation(
            connection, token.operation_id, error, execution_generation=token.execution_generation
        )
        return True

    def receipt(self, section: str, scope_id: str, data_generation: str) -> ConfigurationReceipt:
        row = self.read(section, scope_id)
        return ConfigurationReceipt(
            section=section,
            scope_id=scope_id or None,
            data_generation=data_generation,
            saved_revision=row["saved_revision"],
            active_revision=row["active_revision"],
            application_state=row["application_state"],
            apply_operation_id=row["apply_operation_id"],
            error=Error.model_validate_json(row["error_json"]) if row["error_json"] else None,
        )
