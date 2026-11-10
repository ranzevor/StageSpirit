import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from stagespirit_mcp import __version__

ROOT = Path(__file__).resolve().parents[2]


def run_uv(*arguments: str, cwd: Path = ROOT) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    result = subprocess.run(
        [uv, *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def build_distributions(source: Path, destination: Path) -> tuple[Path, Path]:
    run_uv(
        "build",
        "--sdist",
        "--wheel",
        "--no-build-isolation",
        "--out-dir",
        str(destination),
        cwd=source,
    )
    (wheel,) = destination.glob("*.whl")
    (sdist,) = destination.glob("*.tar.gz")
    return wheel, sdist


@pytest.fixture(scope="module")
def installed_wheel(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, Path]:
    workdir = tmp_path_factory.mktemp("wheel 中文")
    wheel, sdist = build_distributions(ROOT, workdir / "dist")
    source = workdir / "source"
    with tarfile.open(sdist) as archive:
        archive.extractall(source, filter="data")
    (source_root,) = source.iterdir()
    for relative in (
        "docs/assets/stagespirit.svg",
        ".github/scripts/vendor/CommonMark-LICENSE.txt",
        ".github/scripts/NOTICE.md",
        "scripts/check_docs.cjs",
        "examples/mcp/runtime_status.py",
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        "uv.lock",
    ):
        assert (source_root / relative).read_bytes() == (ROOT / relative).read_bytes()
    run_uv(
        "build",
        "--wheel",
        "--no-build-isolation",
        "--out-dir",
        str(workdir / "rebuilt"),
        cwd=source_root,
    )
    (rebuilt_wheel,) = (workdir / "rebuilt").glob("*.whl")
    with zipfile.ZipFile(wheel) as original, zipfile.ZipFile(rebuilt_wheel) as rebuilt:
        assert sorted(original.namelist()) == sorted(rebuilt.namelist())
        for name in original.namelist():
            assert original.read(name) == rebuilt.read(name), name
    requirements = workdir / "requirements.txt"
    run_uv(
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--format",
        "requirements-txt",
        "--output-file",
        str(requirements),
    )
    environment = workdir / "environment"
    run_uv("venv", "--python", sys.executable, str(environment), cwd=workdir)
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    run_uv(
        "pip",
        "sync",
        "--python",
        str(python),
        "--require-hashes",
        "--index-url",
        "https://pypi.org/simple",
        str(requirements),
        cwd=workdir,
    )
    run_uv("pip", "install", "--python", str(python), "--no-deps", str(wheel), cwd=workdir)
    return workdir, python, wheel


def test_installed_import_cli_and_license(installed_wheel: tuple[Path, Path, Path]) -> None:
    workdir, python, wheel = installed_wheel
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    probe = subprocess.run(
        [
            str(python),
            "-c",
            "import json, stagespirit_mcp; print(json.dumps("
            "{'path': stagespirit_mcp.__file__, 'version': stagespirit_mcp.__version__}))",
        ],
        cwd=workdir,
        env=environment,
        check=True,
        capture_output=True,
        timeout=20,
    )
    imported = json.loads(probe.stdout)
    assert Path(imported["path"]).is_relative_to(workdir / "environment")
    assert imported["version"] == __version__
    command = python.with_name("stagespirit.exe" if os.name == "nt" else "stagespirit")
    for arguments, expected in [
        (["--version"], __version__),
        (["--help"], "serve"),
        (["serve", "--help"], "--profile"),
    ]:
        result = subprocess.run(
            [str(command), *arguments],
            cwd=workdir,
            env=environment,
            check=True,
            capture_output=True,
            timeout=20,
        )
        assert expected in result.stdout.decode("utf-8")
        assert result.stderr == b""
    with zipfile.ZipFile(wheel) as archive:
        (license_path,) = (
            name for name in archive.namelist() if name.endswith("/licenses/LICENSE")
        )
        assert archive.read(license_path) == (ROOT / "LICENSE").read_bytes()
        assert all(not name.startswith(("tests/", "docs/")) for name in archive.namelist())


@pytest.mark.asyncio
async def test_installed_cli_mcp(installed_wheel: tuple[Path, Path, Path]) -> None:
    workdir, python, _ = installed_wheel
    command = python.with_name("stagespirit.exe" if os.name == "nt" else "stagespirit")
    parameters = StdioServerParameters(
        command=str(command),
        args=["serve", "--profile", "installed", "--data-dir", str(workdir / "应用 数据")],
        cwd=workdir,
        env={"PYTHONIOENCODING": "gbk", "PYTHONUTF8": "0"},
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=10) as session:
            await session.initialize()
            assert [tool.name for tool in (await session.list_tools()).tools] == ["runtime_status"]
            status = await session.call_tool("runtime_status", {})
            assert not status.is_error
            assert status.structured_content["profile_id"] == "installed"
            assert status.structured_content["version"] == __version__


def test_wheel_build_uses_checkout_independently_of_sdist(tmp_path: Path) -> None:
    source = tmp_path / "project"
    package = source / "src/build_fixture"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
    (package / "wheel_only.txt").write_text("wheel-only fixture\n", encoding="utf-8", newline="\n")
    (source / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling==1.33.0"]\n'
        'build-backend = "hatchling.build"\n'
        '[project]\nname = "stagespirit-build-fixture"\nversion = "0.0.1"\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["src/build_fixture"]\n'
        '[tool.hatch.build.targets.sdist]\ninclude = ["/src", "/pyproject.toml"]\n'
        'exclude = ["/src/build_fixture/wheel_only.txt"]\n',
        encoding="utf-8",
        newline="\n",
    )
    wheel, sdist = build_distributions(source, tmp_path / "dist")
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read("build_fixture/wheel_only.txt") == b"wheel-only fixture\n"
    with tarfile.open(sdist) as archive:
        assert not any(name.endswith("wheel_only.txt") for name in archive.getnames())
        archive.extractall(tmp_path / "extracted", filter="data")
    (extracted,) = (tmp_path / "extracted").iterdir()
    run_uv(
        "build",
        "--wheel",
        "--no-build-isolation",
        "--out-dir",
        str(tmp_path / "rebuilt"),
        cwd=extracted,
    )
    (rebuilt,) = (tmp_path / "rebuilt").glob("*.whl")
    with zipfile.ZipFile(rebuilt) as archive:
        assert "build_fixture/wheel_only.txt" not in archive.namelist()
