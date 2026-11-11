import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from stagespirit_mcp.runtime.contracts import Error, ErrorContext
from stagespirit_mcp.runtime.errors import BusinessError, StartupError

_SCHEMA_VERSION = 1
_APPLICATION_ID = 0x53535054

_SCHEMA = (
    """CREATE TABLE runtime_metadata (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        profile_id TEXT NOT NULL,
        data_generation TEXT NOT NULL
    )""",
    """CREATE TABLE runtime_operations (
        operation_id TEXT PRIMARY KEY,
        data_generation TEXT NOT NULL,
        tool TEXT NOT NULL,
        section TEXT NOT NULL,
        scope_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK (revision >= 0),
        idempotency_key TEXT,
        execution_generation INTEGER NOT NULL CHECK (execution_generation >= 1),
        state TEXT NOT NULL CHECK (state IN ('running', 'completed', 'failed')),
        recovery_state TEXT NOT NULL,
        error_json TEXT,
        UNIQUE (data_generation, tool, section, scope_id, idempotency_key)
    )""",
    """CREATE INDEX runtime_operations_pending ON runtime_operations(section, scope_id)
        WHERE state = 'running'""",
    """CREATE TABLE settings_sections (
        section TEXT NOT NULL,
        scope_id TEXT NOT NULL,
        saved_revision INTEGER NOT NULL CHECK (saved_revision >= 0),
        values_json TEXT NOT NULL,
        active_revision INTEGER CHECK (active_revision >= 0),
        application_state TEXT NOT NULL
            CHECK (application_state IN ('applying', 'applied', 'failed')),
        apply_operation_id TEXT NOT NULL REFERENCES runtime_operations(operation_id),
        activation_epoch TEXT NOT NULL,
        error_json TEXT,
        PRIMARY KEY (section, scope_id)
    )""",
)


def migrate_v1(connection: sqlite3.Connection) -> None:
    for statement in _SCHEMA:
        connection.execute(statement)


_MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {1: migrate_v1}


class Database:
    def __init__(self, path: Path, profile_id: str, data_generation: str) -> None:
        self.connection = sqlite3.connect(path, isolation_level=None, timeout=2)
        self.connection.row_factory = sqlite3.Row
        try:
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA busy_timeout = 2000")
            version = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
            application = int(self.connection.execute("PRAGMA application_id").fetchone()[0])
            if version > _SCHEMA_VERSION or (version and application != _APPLICATION_ID):
                raise StartupError("MIGRATION_REQUIRED：数据库格式不受当前版本支持。")
            if (
                not version
                and self.connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
                ).fetchone()
            ):
                raise StartupError("MIGRATION_REQUIRED：数据库没有可识别的版本。")
            with self.transaction() as connection:
                for target in range(version + 1, _SCHEMA_VERSION + 1):
                    _MIGRATIONS[target](connection)
                    connection.execute(f"PRAGMA user_version = {target}")
                if not version:
                    connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
                    connection.execute(
                        "INSERT INTO runtime_metadata VALUES (1, ?, ?)",
                        (profile_id, data_generation),
                    )
                row = connection.execute(
                    "SELECT * FROM runtime_metadata WHERE singleton = 1"
                ).fetchone()
                if row is None or row["profile_id"] != profile_id:
                    raise StartupError("数据库与运行配置身份不一致。")
                if row["data_generation"] != data_generation:
                    raise StartupError("数据库与维护状态的数据代际不一致。")
            mode = self.connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            if mode != "wal":
                raise StartupError("配置数据库无法启用 WAL。")
            self.connection.execute("PRAGMA synchronous = FULL")
        except BaseException:
            self.connection.close()
            raise

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
            self.connection.execute("COMMIT")
        except BaseException:
            if self.connection.in_transaction:
                self.connection.execute("ROLLBACK")
            raise

    def check_generation(self, connection: sqlite3.Connection, data_generation: str) -> None:
        row = connection.execute(
            "SELECT data_generation FROM runtime_metadata WHERE singleton = 1"
        ).fetchone()
        if row is None:
            raise StartupError("数据库缺少数据代际。")
        if data_generation != row["data_generation"]:
            raise BusinessError(
                Error(
                    code="DATA_GENERATION_CHANGED",
                    message="数据代际已改变，请读取当前运行状态和配置修订。",
                    retryable=False,
                    context=ErrorContext(current_data_generation=row["data_generation"]),
                )
            )

    def close(self) -> None:
        self.connection.close()
