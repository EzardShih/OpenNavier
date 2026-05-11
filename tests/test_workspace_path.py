import pytest
from opennavier_core.workspace_path import normalize_workspace_relative_path


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("case/system/controlDict", "case/system/controlDict"),
        ("case\\system\\controlDict", "case/system/controlDict"),
        ("./case/system/controlDict", "case/system/controlDict"),
    ],
)
def test_normalize_workspace_relative_path_uses_portable_posix_shape(
    value: str,
    expected: str,
) -> None:
    assert normalize_workspace_relative_path(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "../outside",
        "/tmp/outside",
        "C:case",
        "C:/outside/case",
        "//server/share/case",
        "~/case",
        "case/name:with-colon",
    ],
)
def test_normalize_workspace_relative_path_rejects_host_specific_or_unsafe_paths(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        normalize_workspace_relative_path(value)
