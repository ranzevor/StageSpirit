import asyncio
import logging
import sqlite3
import subprocess
import sys
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from threading import Barrier, Event

import pytest
from pydantic import BaseModel

from stagespirit_mcp.bootstrap.application import open_runtime
from stagespirit_mcp.infrastructure.storage import database as database_module
from stagespirit_mcp.infrastructure.storage.database import Database
from stagespirit_mcp.modules.settings.repository import SettingsRepository
from stagespirit_mcp.modules.settings.service import SettingsService
from stagespirit_mcp.runtime.configuration import RuntimeConfiguration, RuntimeSettings
from stagespirit_mcp.runtime.errors import BusinessError, StartupError
from stagespirit_mcp.runtime.operations import get_operation


@pytest.mark.asyncio
async def test_acc_cfg_001_saved_and_active_configuration_survive_restart(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as runtime:
        initial = await runtime.settings.get("runtime")
        assert initial["saved_revision"] == initial["active_revision"] == 0
        assert initial["values"] == initial["active_values"] == {"log_level": "WARNING"}
        receipt = await runtime.settings.save(
            section="runtime",
            scope_id=None,
            data_generation=runtime.data_generation,
            expected_revision=0,
            changes={"log_level": "ERROR"},
        )
        assert receipt.saved_revision == receipt.active_revision == 1
        assert receipt.application_state == "applied"
        assert logging.getLogger("mcp").getEffectiveLevel() == logging.ERROR
        operation_id = receipt.apply_operation_id
        generation = runtime.data_generation
    with open_runtime("default", tmp_path) as restored:
        current = await restored.settings.get("runtime")
        assert current["values"] == current["active_values"] == {"log_level": "ERROR"}
        assert current["saved_revision"] == current["active_revision"] == 1
        assert restored.data_generation == generation
        assert (await restored.settings.operation_get(operation_id)).state == "completed"
        with open_runtime("other", tmp_path) as isolated:
            other = await isolated.settings.get("runtime")
            assert other["values"] == {"log_level": "WARNING"}
            with pytest.raises(BusinessError) as missing:
                await isolated.settings.operation_get(operation_id)
            assert missing.value.error.code == "NOT_FOUND"
    directory = tmp_path / "profiles/default"
    with sqlite3.connect(directory / "state.sqlite3") as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert not list(tmp_path.rglob("*backup*"))


@pytest.mark.asyncio
async def test_acc_cfg_002_concurrent_save_has_one_winner(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as runtime:

        async def save(level: str):
            return await runtime.settings.save(
                section="runtime",
                scope_id=None,
                data_generation=runtime.data_generation,
                expected_revision=0,
                changes={"log_level": level},
            )

        results = await asyncio.gather(save("ERROR"), save("INFO"), return_exceptions=True)
        success = [item for item in results if not isinstance(item, BaseException)]
        conflicts = [item for item in results if isinstance(item, BusinessError)]
        assert len(success) == len(conflicts) == 1
        assert conflicts[0].error.code == "REVISION_CONFLICT"
        current = await runtime.settings.get("runtime")
        assert current["saved_revision"] == current["active_revision"] == 1
        assert current["values"] == current["active_values"]
        assert current["values"]["log_level"] in ("ERROR", "INFO")


def test_acc_cfg_002_sqlite_conditional_write_across_connections(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as runtime:
        generation = runtime.data_generation
    barrier = Barrier(2)
    path = tmp_path / "profiles/default/state.sqlite3"

    def write(level: str):
        database = Database(path, "default", generation)
        try:
            repository = SettingsRepository(database)
            assert repository.read("runtime", "")["saved_revision"] == 0
            barrier.wait(timeout=10)
            return repository.begin(
                section="runtime",
                scope_id="",
                data_generation=generation,
                revision=0,
                epoch=level,
                values={"log_level": level},
                tool="settings_save",
            )
        except BusinessError as error:
            return error.error.code
        finally:
            database.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(write, "ERROR")
        second = workers.submit(write, "INFO")
        results = [first.result(timeout=15), second.result(timeout=15)]
    assert sum(item == "REVISION_CONFLICT" for item in results) == 1
    with open_runtime("default", tmp_path) as runtime:
        current = asyncio.run(runtime.settings.get("runtime"))
        assert current["saved_revision"] == current["active_revision"] == 1


@pytest.mark.asyncio
async def test_acc_cfg_002_application_failure_retains_saved_and_previous_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with open_runtime("default", tmp_path) as runtime:
        original = runtime.configuration.activate

        def fail(candidate: BaseModel | None) -> None:
            if isinstance(candidate, RuntimeSettings) and candidate.log_level == "ERROR":
                raise RuntimeError("injected activation failure")
            original(candidate)

        with monkeypatch.context() as patch:
            patch.setattr(runtime.configuration, "activate", fail)
            receipt = await runtime.settings.save(
                section="runtime",
                scope_id=None,
                data_generation=runtime.data_generation,
                expected_revision=0,
                changes={"log_level": "ERROR"},
            )
        assert receipt.application_state == "failed"
        assert (receipt.saved_revision, receipt.active_revision) == (1, 0)
        assert receipt.error.code == "CONFIGURATION_APPLY_FAILED"
        current = await runtime.settings.get("runtime")
        assert current["values"] == {"log_level": "ERROR"}
        assert current["active_values"] == {"log_level": "WARNING"}
        failure = await runtime.settings.operation_get(receipt.apply_operation_id)
        assert failure.state == "failed" and failure.effect_state == "none"
        applied = await runtime.settings.apply(
            section="runtime",
            scope_id=None,
            data_generation=runtime.data_generation,
            revision=1,
            idempotency_key="retry-1",
        )
        assert applied.state == "completed"
        after = await runtime.settings.get("runtime")
        assert after["saved_revision"] == after["active_revision"] == 1
        assert after["active_values"] == {"log_level": "ERROR"}


@pytest.mark.asyncio
async def test_apply_idempotency_and_revision_survive_restart(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as runtime:
        arguments = dict(
            section="runtime",
            scope_id=None,
            data_generation=runtime.data_generation,
            revision=0,
            idempotency_key="apply-default",
        )
        first, duplicate = await asyncio.gather(
            runtime.settings.apply(**arguments), runtime.settings.apply(**arguments)
        )
        assert first == duplicate and first.state == "completed"
        await runtime.settings.save(
            section="runtime",
            scope_id=None,
            data_generation=runtime.data_generation,
            expected_revision=0,
            changes={"log_level": "ERROR"},
        )
        assert await runtime.settings.apply(**arguments) == first
        with pytest.raises(BusinessError) as reused:
            await runtime.settings.apply(**(arguments | {"revision": 1}))
        assert reused.value.error.code == "IDEMPOTENCY_CONFLICT"
        with pytest.raises(BusinessError) as older:
            await runtime.settings.apply(**(arguments | {"idempotency_key": "stale"}))
        assert older.value.error.code == "REVISION_CONFLICT"
    with open_runtime("default", tmp_path) as runtime:
        assert await runtime.settings.apply(**arguments) == first
        assert (await runtime.settings.get("runtime"))["active_values"] == {"log_level": "ERROR"}


@pytest.mark.asyncio
async def test_generation_precedes_revision_and_invalid_scope_is_not_saved(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as runtime:
        before = await runtime.settings.get("runtime")
        with pytest.raises(BusinessError) as stale:
            await runtime.settings.save(
                section="runtime",
                scope_id=None,
                data_generation="old",
                expected_revision=99,
                changes={"log_level": "ERROR"},
            )
        assert stale.value.error.code == "DATA_GENERATION_CHANGED"
        assert stale.value.error.context.current_data_generation == runtime.data_generation
        for section, scope in [("speech", None), ("runtime", "other-profile")]:
            with pytest.raises(BusinessError) as invalid:
                await runtime.settings.save(
                    section=section,
                    scope_id=scope,
                    data_generation=runtime.data_generation,
                    expected_revision=0,
                    changes={"log_level": "ERROR"},
                )
            assert invalid.value.error.code == "INVALID_ARGUMENT"
        assert await runtime.settings.get("runtime") == before


@pytest.mark.asyncio
async def test_acc_cfg_002_failed_save_rolls_back_operation_and_revision(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as runtime:
        before = await runtime.settings.get("runtime")
        path = tmp_path / "profiles/default/state.sqlite3"
        with sqlite3.connect(path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM runtime_operations").fetchone()[0]
            connection.execute(
                """CREATE TRIGGER reject_configuration BEFORE UPDATE ON settings_sections
                BEGIN SELECT RAISE(ABORT, 'injected write failure'); END"""
            )
        with pytest.raises(BusinessError) as failure:
            await runtime.settings.save(
                section="runtime",
                scope_id=None,
                data_generation=runtime.data_generation,
                expected_revision=0,
                changes={"log_level": "ERROR"},
            )
        assert failure.value.error.code == "STORAGE_ERROR"
        assert await runtime.settings.get("runtime") == before
        with sqlite3.connect(path) as connection:
            assert (
                connection.execute("SELECT COUNT(*) FROM runtime_operations").fetchone()[0] == count
            )


@pytest.mark.asyncio
async def test_failed_activation_commit_restores_memory_and_can_reapply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with open_runtime("default", tmp_path) as runtime:
        original = Database.transaction

        @contextmanager
        def reject_completion(database: Database) -> Generator[sqlite3.Connection]:
            with original(database) as connection:
                yield connection
                row = connection.execute("SELECT * FROM settings_sections").fetchone()
                if row and row["saved_revision"] == 1 and row["application_state"] == "applied":
                    raise sqlite3.OperationalError("injected completion commit failure")

        with monkeypatch.context() as patch:
            patch.setattr(Database, "transaction", reject_completion)
            with pytest.raises(BusinessError) as failure:
                await runtime.settings.save(
                    section="runtime",
                    scope_id=None,
                    data_generation=runtime.data_generation,
                    expected_revision=0,
                    changes={"log_level": "ERROR"},
                )
        assert failure.value.error.code == "STORAGE_ERROR"
        current = await runtime.settings.get("runtime")
        assert (current["saved_revision"], current["active_revision"]) == (1, 0)
        assert current["application_state"] == "applying"
        assert current["active_values"] == {"log_level": "WARNING"}
        retry = await runtime.settings.apply(
            section="runtime",
            scope_id=None,
            data_generation=runtime.data_generation,
            revision=1,
            idempotency_key="after-commit-failure",
        )
        assert retry.state == "completed"
        assert (
            await runtime.settings.operation_get(current["apply_operation_id"])
        ).state == "failed"


def test_acc_cfg_004_process_exit_after_save_restores_original_activation(tmp_path: Path) -> None:
    script = """
import asyncio, os, sys
from pathlib import Path
from stagespirit_mcp.bootstrap.application import open_runtime
async def main():
    with open_runtime("default", Path(sys.argv[1])) as runtime:
        runtime.settings._activate = lambda *args: os._exit(0)
        await runtime.settings.save(
            section="runtime", scope_id=None, data_generation=runtime.data_generation,
            expected_revision=0, changes={"log_level": "ERROR"}
        )
asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script, str(tmp_path)],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0 and not result.stderr
    path = tmp_path / "profiles/default/state.sqlite3"
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT saved_revision, active_revision, application_state, apply_operation_id "
            "FROM settings_sections"
        ).fetchone()
        assert row[:3] == (1, 0, "applying")
        operation_id = row[3]
    with open_runtime("default", tmp_path) as runtime:
        current = asyncio.run(runtime.settings.get("runtime"))
        assert current["saved_revision"] == current["active_revision"] == 1
        assert current["active_values"] == {"log_level": "ERROR"}
        original = asyncio.run(runtime.settings.operation_get(operation_id))
        assert original.state == "completed"
        assert original.execution_generation == 2
        assert original.recovery.state == "resolved"


def test_acc_cfg_004_old_revision_epoch_and_attempt_cannot_complete_new_activation(
    tmp_path: Path,
) -> None:
    with open_runtime("default", tmp_path) as runtime:
        generation = runtime.data_generation
    database = Database(tmp_path / "profiles/default/state.sqlite3", "default", generation)
    try:
        repository = SettingsRepository(database)
        older = repository.begin(
            section="runtime",
            scope_id="",
            data_generation=generation,
            revision=0,
            epoch="instance-1",
            values={"log_level": "INFO"},
            tool="settings_save",
        )
        current = repository.begin(
            section="runtime",
            scope_id="",
            data_generation=generation,
            revision=1,
            epoch="instance-2",
            values={"log_level": "ERROR"},
            tool="settings_save",
        )
        with database.transaction() as connection:
            assert repository.complete(connection, older) is False
            assert repository.complete(connection, replace(current, epoch="old-instance")) is False
            assert (
                repository.complete(connection, replace(current, data_generation="old-data"))
                is False
            )
            connection.execute(
                "UPDATE runtime_operations SET execution_generation = 2 WHERE operation_id = ?",
                (current.operation_id,),
            )
            assert repository.complete(connection, current) is False
            assert get_operation(connection, current.operation_id).state == "running"
            assert repository.complete(connection, replace(current, execution_generation=2)) is True
        assert repository.read("runtime", "")["active_revision"] == 2
    finally:
        database.close()


@pytest.mark.asyncio
async def test_cancelled_wait_keeps_accepted_configuration_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = Event(), Event()
    with open_runtime("default", tmp_path) as runtime:
        original = runtime.configuration.activate

        def delayed(candidate: BaseModel | None) -> None:
            if isinstance(candidate, RuntimeSettings) and candidate.log_level == "ERROR":
                entered.set()
                if not release.wait(timeout=10):
                    raise TimeoutError("test barrier not released")
            original(candidate)

        with monkeypatch.context() as patch:
            patch.setattr(runtime.configuration, "activate", delayed)
            task = asyncio.create_task(
                runtime.settings.save(
                    section="runtime",
                    scope_id=None,
                    data_generation=runtime.data_generation,
                    expected_revision=0,
                    changes={"log_level": "ERROR"},
                )
            )
            try:
                assert await asyncio.to_thread(entered.wait, 5)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            finally:
                release.set()
            current = await runtime.settings.get("runtime")
        assert current["saved_revision"] == current["active_revision"] == 1
        assert current["active_values"] == {"log_level": "ERROR"}


@pytest.mark.asyncio
async def test_bounded_configuration_queue_rejects_unaccepted_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = Event(), Event()
    participant = RuntimeConfiguration()
    service = SettingsService(tmp_path, "test", "generation", (participant,), queue_capacity=1)
    original = participant.activate

    def delayed(candidate: BaseModel | None) -> None:
        if isinstance(candidate, RuntimeSettings) and candidate.log_level == "ERROR":
            entered.set()
            if not release.wait(timeout=10):
                raise TimeoutError("test barrier not released")
        original(candidate)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(participant, "activate", delayed)
            task = asyncio.create_task(
                service.save(
                    section="runtime",
                    scope_id=None,
                    data_generation="generation",
                    expected_revision=0,
                    changes={"log_level": "ERROR"},
                )
            )
            try:
                assert await asyncio.to_thread(entered.wait, 5)
                with pytest.raises(BusinessError) as full:
                    await service.get("runtime")
                assert full.value.error.code == "QUEUE_FULL"
            finally:
                release.set()
            assert (await task).application_state == "applied"
        assert (await service.get("runtime"))["saved_revision"] == 1
    finally:
        service.close()


def test_acc_cfg_003_migration_failure_rolls_back_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed_migration(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE interrupted (value TEXT)")
        raise sqlite3.OperationalError("injected migration failure")

    path = tmp_path / "state.sqlite3"
    with monkeypatch.context() as patch:
        patch.setitem(database_module._MIGRATIONS, 1, failed_migration)
        with pytest.raises(sqlite3.OperationalError):
            Database(path, "default", "generation")
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute("SELECT name FROM sqlite_master").fetchall() == []
    database = Database(path, "default", "generation")
    database.close()


@pytest.mark.parametrize("mismatch", ["version", "profile", "generation", "corrupt"])
def test_incompatible_database_preserves_data_and_releases_lock(
    tmp_path: Path, mismatch: str
) -> None:
    with open_runtime("default", tmp_path):
        pass
    path = tmp_path / "profiles/default/state.sqlite3"
    if mismatch == "corrupt":
        path.write_bytes(b"invalid database")
    else:
        with sqlite3.connect(path) as connection:
            if mismatch == "version":
                connection.execute("PRAGMA user_version = 2")
            else:
                column = "profile_id" if mismatch == "profile" else "data_generation"
                connection.execute(f"UPDATE runtime_metadata SET {column} = 'different'")
    original = path.read_bytes()
    with pytest.raises(StartupError):
        with open_runtime("default", tmp_path):
            pytest.fail("Incompatible database was accepted")
    assert path.read_bytes() == original
    lock = tmp_path / "profiles/default/instance.lock"
    from filelock import FileLock

    with FileLock(lock).acquire(timeout=0):
        pass


@pytest.mark.asyncio
async def test_pending_apply_resumes_same_operation_after_commit_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with open_runtime("default", tmp_path) as runtime:
        original = Database.transaction

        @contextmanager
        def reject_apply_completion(database: Database) -> Generator[sqlite3.Connection]:
            with original(database) as connection:
                yield connection
                row = connection.execute(
                    "SELECT s.application_state, o.tool FROM settings_sections s "
                    "JOIN runtime_operations o ON o.operation_id = s.apply_operation_id"
                ).fetchone()
                if row["tool"] == "settings_apply" and row["application_state"] == "applied":
                    raise sqlite3.OperationalError("injected apply completion failure")

        arguments = dict(
            section="runtime",
            scope_id=None,
            data_generation=runtime.data_generation,
            revision=0,
            idempotency_key="interrupted-apply",
        )
        with monkeypatch.context() as patch:
            patch.setattr(Database, "transaction", reject_apply_completion)
            with pytest.raises(BusinessError) as failure:
                await runtime.settings.apply(**arguments)
        assert failure.value.error.code == "STORAGE_ERROR"
        pending = await runtime.settings.get("runtime")
        assert pending["application_state"] == "applying"
        resumed = await runtime.settings.apply(**arguments)
        assert resumed.state == "completed"
        assert resumed.operation_id == pending["apply_operation_id"]
        detail = await runtime.settings.operation_get(resumed.operation_id)
        assert detail.execution_generation == 2 and detail.recovery.state == "resolved"


def test_pending_operation_recovery_uses_index_with_large_completed_history(tmp_path: Path) -> None:
    with open_runtime("default", tmp_path) as runtime:
        generation = runtime.data_generation
    database = Database(tmp_path / "profiles/default/state.sqlite3", "default", generation)
    try:
        with database.transaction() as connection:
            connection.executemany(
                """INSERT INTO runtime_operations
                    (operation_id, data_generation, tool, section, scope_id, revision,
                     execution_generation, state, recovery_state)
                    VALUES (?, ?, 'configuration_activate', 'runtime', '',
                            0, 1, 'completed', 'idle')""",
                ((f"history-{number}", generation) for number in range(10000)),
            )
        repository = SettingsRepository(database)
        pending = repository.begin(
            section="runtime",
            scope_id="",
            data_generation=generation,
            revision=0,
            epoch="indexed-recovery",
            values={"log_level": "ERROR"},
            tool="settings_save",
        )
        query = (
            "SELECT operation_id FROM runtime_operations "
            "WHERE section = ? AND scope_id = ? AND state = 'running' "
            "AND operation_id != ?"
        )
        parameters = ("runtime", "", "different-operation")
        plan = database.connection.execute("EXPLAIN QUERY PLAN " + query, parameters).fetchall()
        assert any("USING INDEX runtime_operations_pending" in row[3] for row in plan)
        assert [row[0] for row in database.connection.execute(query, parameters)] == [
            pending.operation_id
        ]
    finally:
        database.close()
