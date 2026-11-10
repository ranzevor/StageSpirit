from pathlib import Path

import pytest

from stagespirit_mcp.infrastructure import paths


@pytest.mark.parametrize("profile_id", ["default", "a", "abc-123_xyz", "a" * 64])
def test_profile_directory(tmp_path: Path, profile_id: str) -> None:
    assert paths.profile_directory(tmp_path, profile_id) == tmp_path / "profiles" / profile_id


@pytest.mark.parametrize(
    "profile_id",
    [
        "",
        ".",
        "..",
        "../other",
        "a/b",
        "a\\b",
        "中文",
        "Default",
        "a" * 65,
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "lpt9",
        "profile ",
        "-profile",
    ],
)
def test_invalid_profile_is_rejected(tmp_path: Path, profile_id: str) -> None:
    with pytest.raises(ValueError):
        paths.profile_directory(tmp_path, profile_id)
    assert not list(tmp_path.iterdir())


def test_default_user_data_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "user_data_path", lambda *args, **kwargs: tmp_path)
    assert paths.profile_directory(None, "default") == tmp_path / "profiles" / "default"
