import asyncio
import json
import logging
import sqlite3
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from stagespirit_mcp.infrastructure.storage.database import Database
from stagespirit_mcp.modules.settings.models import ConfigurationReceipt
from stagespirit_mcp.modules.settings.ports import ConfigurationParticipant
from stagespirit_mcp.modules.settings.repository import (
    ActivationToken,
    SettingsRepository,
    revision_conflict,
)
from stagespirit_mcp.runtime.contracts import Error, OperationDetail, OperationReceipt
from stagespirit_mcp.runtime.errors import BusinessError, StartupError
from stagespirit_mcp.runtime.operations import (
    create_operation,
    finish_operation,
    get_operation,
    operation_receipt,
)

T = TypeVar("T")
_LOGGER = logging.getLogger("stagespirit.settings")


def invalid_configuration(error: ValidationError) -> BusinessError:
    first = error.errors(include_input=False, include_url=False)[0]
    field = ".".join(str(part) for part in first["loc"]) or "changes"
    return BusinessError(
        Error(
            code="INVALID_ARGUMENT",
            message="配置字段不符合该分区的类型或取值约束。",
            retryable=False,
            field=field,
            action="按工具输入 Schema 修正字段后重新提交。",
        )
    )


class SettingsService:
    def __init__(
        self,
        directory: Path,
        profile_id: str,
        data_generation: str,
        participants: tuple[ConfigurationParticipant, ...],
        *,
        queue_capacity: int = 64,
    ) -> None:
        self.data_generation = data_generation
        self.epoch = str(uuid4())
        self._participants = {(p.section, p.scope_id or ""): p for p in participants}
        if len(self._participants) != len(participants):
            raise ValueError("配置参与者范围重复。")
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="stagespirit-settings"
        )
        self._slots = BoundedSemaphore(queue_capacity)
        self._lifecycle_lock = Lock()
        self._closed = False
        try:
            self._executor.submit(self._initialize, directory, profile_id).result()
        except (ValidationError, ValueError) as error:
            self._executor.shutdown(wait=True)
            raise StartupError("保存的配置无法由当前版本读取，原数据已保留。") from error
        except sqlite3.Error as error:
            self._executor.shutdown(wait=True)
            raise StartupError("配置数据库无法读取或迁移，原数据已保留。") from error
        except BaseException:
            self._executor.shutdown(wait=True)
            raise

    def _initialize(self, directory: Path, profile_id: str) -> None:
        try:
            self._database = Database(directory / "state.sqlite3", profile_id, self.data_generation)
        except sqlite3.Error as error:
            raise StartupError("配置数据库无法读取或迁移，原数据已保留。") from error
        self._repository = SettingsRepository(self._database)
        try:
            for (section, scope_id), participant in self._participants.items():
                row = self._database.connection.execute(
                    "SELECT * FROM settings_sections WHERE section = ? AND scope_id = ?",
                    (section, scope_id),
                ).fetchone()
                values: dict[str, object] = (
                    json.loads(row["values_json"]) if row else participant.defaults()
                )
                candidate = participant.prepare(values)
                with self._database.transaction() as connection:
                    if row:
                        revision = row["saved_revision"]
                        previous = get_operation(connection, row["apply_operation_id"])
                        if previous.state == "running":
                            operation_id = previous.operation_id
                            execution_generation = previous.execution_generation + 1
                            connection.execute(
                                """UPDATE runtime_operations SET execution_generation = ?,
                                    recovery_state = 'running' WHERE operation_id = ?""",
                                (execution_generation, operation_id),
                            )
                        else:
                            operation_id = create_operation(
                                connection,
                                data_generation=self.data_generation,
                                tool="configuration_activate",
                                section=section,
                                scope_id=scope_id,
                                revision=revision,
                            )
                            execution_generation = 1
                        connection.execute(
                            """UPDATE settings_sections SET active_revision = NULL,
                                application_state = 'applying', apply_operation_id = ?,
                                activation_epoch = ?, error_json = NULL
                                WHERE section = ? AND scope_id = ?""",
                            (operation_id, self.epoch, section, scope_id),
                        )
                    else:
                        revision = 0
                        execution_generation = 1
                        operation_id = create_operation(
                            connection,
                            data_generation=self.data_generation,
                            tool="configuration_activate",
                            section=section,
                            scope_id=scope_id,
                            revision=0,
                        )
                        connection.execute(
                            """INSERT INTO settings_sections
                                (section, scope_id, saved_revision, values_json, active_revision,
                                 application_state, apply_operation_id, activation_epoch)
                                VALUES (?, ?, 0, ?, NULL, 'applying', ?, ?)""",
                            (
                                section,
                                scope_id,
                                candidate.model_dump_json(),
                                operation_id,
                                self.epoch,
                            ),
                        )
                    stale = connection.execute(
                        """SELECT operation_id FROM runtime_operations
                            WHERE section = ? AND scope_id = ? AND state = 'running'
                            AND operation_id != ?""",
                        (section, scope_id, operation_id),
                    ).fetchall()
                    for pending in stale:
                        finish_operation(
                            connection, pending["operation_id"], revision_conflict().error
                        )
                token = ActivationToken(
                    section,
                    scope_id,
                    revision,
                    self.data_generation,
                    self.epoch,
                    operation_id,
                    execution_generation,
                )
                self._activate(token, participant, candidate)
        except BaseException:
            for participant in self._participants.values():
                participant.activate(None)
            self._database.close()
            raise

    async def _run(self, function: Callable[[], T]) -> T:
        with self._lifecycle_lock:
            if self._closed:
                raise BusinessError(
                    Error(
                        code="SERVICE_CLOSING",
                        message="服务正在关闭，尚未受理本次请求。",
                        retryable=True,
                    )
                )
            if not self._slots.acquire(blocking=False):
                raise BusinessError(
                    Error(
                        code="QUEUE_FULL",
                        message="配置工作队列已满，尚未受理本次请求。",
                        retryable=True,
                    )
                )
            try:
                future: Future[T] = self._executor.submit(function)
            except BaseException:
                self._slots.release()
                raise
            future.add_done_callback(lambda _: self._slots.release())
        waiting = asyncio.wrap_future(future)
        waiting.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
        try:
            return await asyncio.shield(waiting)
        except sqlite3.Error as error:
            _LOGGER.error("配置数据库操作失败：%s", error)
            raise BusinessError(
                Error(
                    code="STORAGE_ERROR",
                    message="配置数据库写入或读取失败，请重新读取修订确认提交结果。",
                    retryable=isinstance(error, sqlite3.OperationalError),
                    action="检查数据目录权限、磁盘空间和数据库占用后，读取当前配置。",
                )
            ) from error

    def _participant(self, section: str, scope_id: str | None) -> ConfigurationParticipant:
        participant = self._participants.get((section, scope_id or ""))
        if participant is None:
            raise BusinessError(
                Error(
                    code="INVALID_ARGUMENT",
                    message="当前版本未提供这个配置分区或作用域。",
                    retryable=False,
                    field="scope_id" if scope_id is not None else "section",
                )
            )
        return participant

    def _activate(
        self, token: ActivationToken, participant: ConfigurationParticipant, candidate: BaseModel
    ) -> None:
        previous = participant.snapshot()
        published = False
        try:
            with self._database.transaction() as connection:
                if not self._repository.current(connection, token):
                    self._repository.complete(connection, token)
                    return
                error: Error | None = None
                try:
                    participant.activate(candidate)
                    published = True
                except BusinessError as failure:
                    error = failure.error.model_copy(update={"operation_id": token.operation_id})
                except Exception:
                    _LOGGER.exception("配置分区 %s 的激活失败。", token.section)
                    error = Error(
                        code="CONFIGURATION_APPLY_FAILED",
                        message="运行模块应用配置失败，已保留原活动配置。",
                        retryable=True,
                        operation_id=token.operation_id,
                        action="读取配置状态后，用新的操作键再次应用当前保存修订。",
                    )
                self._repository.complete(connection, token, error)
        except BaseException:
            if published:
                participant.activate(previous)
            raise

    async def get(self, section: str, scope_id: str | None = None) -> dict[str, object]:
        def read() -> dict[str, object]:
            participant = self._participant(section, scope_id)
            row = self._repository.read(section, scope_id or "")
            active = participant.snapshot()
            return {
                **self._repository.receipt(
                    section, scope_id or "", self.data_generation
                ).model_dump(),
                "values": json.loads(row["values_json"]),
                "active_values": active.model_dump() if active else None,
            }

        return await self._run(read)

    async def save(
        self,
        *,
        section: str,
        scope_id: str | None,
        data_generation: str,
        expected_revision: int,
        changes: dict[str, object],
    ) -> ConfigurationReceipt:
        def write() -> ConfigurationReceipt:
            self._database.check_generation(self._database.connection, data_generation)
            participant = self._participant(section, scope_id)
            row = self._repository.read(section, scope_id or "")
            if row["saved_revision"] != expected_revision:
                raise revision_conflict()
            current: dict[str, object] = json.loads(row["values_json"])
            try:
                candidate = participant.prepare(current | changes)
            except ValidationError as error:
                raise invalid_configuration(error) from error
            token = self._repository.begin(
                section=section,
                scope_id=scope_id or "",
                data_generation=data_generation,
                revision=expected_revision,
                epoch=self.epoch,
                values=candidate.model_dump(),
                tool="settings_save",
            )
            self._activate(token, participant, candidate)
            return self._repository.receipt(section, scope_id or "", self.data_generation)

        return await self._run(write)

    async def apply(
        self,
        *,
        section: str,
        scope_id: str | None,
        data_generation: str,
        revision: int,
        idempotency_key: str,
    ) -> OperationReceipt:
        def reapply() -> OperationReceipt:
            connection = self._database.connection
            existing = connection.execute(
                """SELECT operation_id, revision FROM runtime_operations
                    WHERE data_generation = ? AND tool = 'settings_apply'
                    AND section = ? AND scope_id = ? AND idempotency_key = ?""",
                (data_generation, section, scope_id or "", idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["revision"] != revision:
                    raise BusinessError(
                        Error(
                            code="IDEMPOTENCY_CONFLICT",
                            message="同一操作键对应的配置修订不同。",
                            retryable=False,
                            field="idempotency_key",
                        )
                    )
                detail = get_operation(connection, existing["operation_id"])
                if detail.state == "running":
                    self._database.check_generation(connection, data_generation)
                    participant = self._participant(section, scope_id)
                    row = self._repository.read(section, scope_id or "")
                    if row["apply_operation_id"] != detail.operation_id:
                        with self._database.transaction() as transaction:
                            finish_operation(
                                transaction, detail.operation_id, revision_conflict().error
                            )
                    else:
                        candidate = participant.prepare(json.loads(row["values_json"]))
                        generation = detail.execution_generation + 1
                        with self._database.transaction() as transaction:
                            transaction.execute(
                                """UPDATE runtime_operations SET execution_generation = ?,
                                    recovery_state = 'running' WHERE operation_id = ?""",
                                (generation, detail.operation_id),
                            )
                            transaction.execute(
                                """UPDATE settings_sections SET activation_epoch = ?
                                    WHERE section = ? AND scope_id = ?""",
                                (self.epoch, section, scope_id or ""),
                            )
                        self._activate(
                            ActivationToken(
                                section,
                                scope_id or "",
                                revision,
                                data_generation,
                                self.epoch,
                                detail.operation_id,
                                generation,
                            ),
                            participant,
                            candidate,
                        )
                return operation_receipt(get_operation(connection, detail.operation_id))
            self._database.check_generation(connection, data_generation)
            participant = self._participant(section, scope_id)
            row = self._repository.read(section, scope_id or "")
            if row["saved_revision"] != revision:
                raise BusinessError(
                    revision_conflict().error.model_copy(update={"field": "revision"})
                )
            candidate = participant.prepare(json.loads(row["values_json"]))
            token = self._repository.begin(
                section=section,
                scope_id=scope_id or "",
                data_generation=data_generation,
                revision=revision,
                epoch=self.epoch,
                idempotency_key=idempotency_key,
                tool="settings_apply",
            )
            self._activate(token, participant, candidate)
            return operation_receipt(get_operation(connection, token.operation_id))

        return await self._run(reapply)

    async def operation_get(self, operation_id: str) -> OperationDetail:
        return await self._run(lambda: get_operation(self._database.connection, operation_id))

    def close(self) -> None:
        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            closing = self._executor.submit(self._close)
        try:
            closing.result()
        finally:
            self._executor.shutdown(wait=True)

    def _close(self) -> None:
        try:
            for participant in self._participants.values():
                participant.activate(None)
        finally:
            self._database.close()
