import asyncio
import sys
import types
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if "aiofiles" not in sys.modules:
    class _AsyncFile:
        def __init__(self, path: str, mode: str):
            self._path = path
            self._mode = mode
            self._handle = None

        async def __aenter__(self):  # type: ignore[override]
            self._handle = open(self._path, self._mode)
            return self

        async def __aexit__(self, exc_type, exc, tb):  # type: ignore[override]
            if self._handle:
                self._handle.close()

        async def write(self, data: str) -> None:
            assert self._handle is not None
            self._handle.write(data)

        async def read(self) -> str:
            assert self._handle is not None
            return self._handle.read()

    def _aiofiles_open(path: str, mode: str) -> _AsyncFile:
        return _AsyncFile(path, mode)

    sys.modules["aiofiles"] = types.SimpleNamespace(open=_aiofiles_open)

if "aiohttp" not in sys.modules:
    sys.modules["aiohttp"] = types.SimpleNamespace(web=types.SimpleNamespace())

if "jsonschema" not in sys.modules:
    def _validate(*args, **kwargs):
        return True

    sys.modules["jsonschema"] = types.SimpleNamespace(validate=_validate)

import pytest

from servers.cascade_rules_server import CascadeRulesMCPServer, MCPError


def test_change_summary_required_for_create(tmp_path: Path) -> None:
    async def run() -> None:
        server = CascadeRulesMCPServer(storage_path=str(tmp_path / "storage"), enable_web_ui=False)
        await server.connect()

        try:
            params = {
                "name": "Test Rule",
                "description": "A rule for testing",
                "category": "testing",
                "content": {"key": "value"},
                "created_by": "tester",
            }

            with pytest.raises(MCPError) as exc:
                await server.cascade_rule_create(params)

            assert "change_summary" in str(exc.value)
        finally:
            await server.disconnect()

    asyncio.run(run())


def test_change_summary_persisted_and_audited(tmp_path: Path) -> None:
    async def run() -> None:
        server = CascadeRulesMCPServer(storage_path=str(tmp_path / "storage"), enable_web_ui=False)
        await server.connect()

        try:
            create_params = {
                "name": "Persistent Rule",
                "description": "Created for audit testing",
                "category": "audit",
                "content": {"enabled": True},
                "created_by": "creator",
                "change_summary": "Initial creation",
            }

            create_result = await server.cascade_rule_create(create_params)
            rule_id = create_result["rule"]["id"]
            assert create_result["rule"]["last_change_summary"] == "Initial creation"

            audit_after_create = await server.cascade_rule_audit({})
            assert audit_after_create["entries"][0]["summary"] == "Initial creation"

            update_params = {
                "rule_id": rule_id,
                "description": "Updated description",
                "updated_by": "updater",
                "change_summary": "Refined description",
            }
            update_result = await server.cascade_rule_update(update_params)
            assert update_result["rule"]["last_change_summary"] == "Refined description"

            audit_after_update = await server.cascade_rule_audit({"action": "update"})
            assert audit_after_update["entries"][0]["summary"] == "Refined description"

            delete_params = {
                "rule_id": rule_id,
                "deleted_by": "deleter",
                "change_summary": "Cleaned up obsolete rule",
            }
            delete_result = await server.cascade_rule_delete(delete_params)
            assert delete_result["deleted"] is True

            audit_after_delete = await server.cascade_rule_audit({"action": "delete"})
            assert audit_after_delete["entries"][0]["summary"] == "Cleaned up obsolete rule"
        finally:
            await server.disconnect()

    asyncio.run(run())
