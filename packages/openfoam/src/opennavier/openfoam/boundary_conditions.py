import re
from pathlib import Path

from opennavier_core.diagnostics import DiagnosticResult, DiagnosticStatus

BLOCK_MESH_DICT_PATH = Path("system") / "blockMeshDict"
BOUNDARY_FIELD_PATHS = (
    Path("0") / "U",
    Path("0") / "p",
)

_COMMENT_PATTERN = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def diagnose_boundary_conditions(case_path: Path | str) -> list[DiagnosticResult]:
    root = Path(case_path)
    required_paths = (BLOCK_MESH_DICT_PATH, *BOUNDARY_FIELD_PATHS)
    missing_paths = [
        relative_path
        for relative_path in required_paths
        if not (root / relative_path).exists()
    ]
    present_paths = [
        relative_path for relative_path in required_paths if relative_path not in missing_paths
    ]

    if not present_paths:
        return []

    contents: dict[Path, str] = {}
    unreadable_paths: list[Path] = []
    for relative_path in present_paths:
        path = root / relative_path
        try:
            contents[relative_path] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            unreadable_paths.append(relative_path)

    if unreadable_paths:
        return [
            DiagnosticResult(
                status=DiagnosticStatus.FAIL,
                code="openfoam.boundary_conditions.unreadable",
                message="Could not read OpenFOAM boundary-condition dictionaries.",
                path=str(root),
                details={"unreadable_files": _join_paths(unreadable_paths)},
            )
        ]

    if BLOCK_MESH_DICT_PATH not in contents:
        return [
            DiagnosticResult(
                status=DiagnosticStatus.WARN,
                code="openfoam.boundary_conditions.missing_optional",
                message=(
                    "Boundary-condition validation skipped because dictionary files are missing."
                ),
                path=str(root),
                details={"missing_files": _join_paths(missing_paths)},
            )
        ]

    try:
        mesh_patches = _extract_boundary_patches(contents[BLOCK_MESH_DICT_PATH])
        field_patches = {
            relative_path: _extract_boundary_field_patches(contents[relative_path])
            for relative_path in BOUNDARY_FIELD_PATHS
            if relative_path in contents
        }
    except ValueError as error:
        return [
            DiagnosticResult(
                status=DiagnosticStatus.FAIL,
                code="openfoam.boundary_conditions.unparseable",
                message="Could not parse OpenFOAM boundary-condition dictionaries.",
                path=str(root),
                details={"parse_error": str(error)},
            )
        ]

    mismatch_details = _mismatch_details(mesh_patches, field_patches)
    if mismatch_details:
        return [
            DiagnosticResult(
                status=DiagnosticStatus.FAIL,
                code="openfoam.boundary_conditions.mismatch",
                message="OpenFOAM boundaryField patches do not match blockMeshDict boundaries.",
                path=str(root),
                details=mismatch_details,
            )
        ]

    if missing_paths:
        return [
            DiagnosticResult(
                status=DiagnosticStatus.WARN,
                code="openfoam.boundary_conditions.missing_optional",
                message=(
                    "Boundary-condition validation passed for available dictionaries; "
                    "some files are missing."
                ),
                path=str(root),
                details={"missing_files": _join_paths(missing_paths)},
            )
        ]

    return [
        DiagnosticResult(
            status=DiagnosticStatus.PASS,
            code="openfoam.boundary_conditions.valid",
            message="OpenFOAM boundaryField patches match blockMeshDict boundaries.",
            path=str(root),
            details={
                "patches": _join_names(mesh_patches),
                "fields": _join_names(path.stem for path in BOUNDARY_FIELD_PATHS),
            },
        )
    ]


def _extract_boundary_patches(content: str) -> set[str]:
    section = _extract_section(content, "boundary", "(", ")")
    return _extract_named_blocks(section)


def _extract_boundary_field_patches(content: str) -> set[str]:
    section = _extract_section(content, "boundaryField", "{", "}")
    return _extract_named_blocks(section)


def _extract_section(content: str, keyword: str, opener: str, closer: str) -> str:
    text = _COMMENT_PATTERN.sub("", content)
    match = re.search(rf"\b{re.escape(keyword)}\b", text)
    if match is None:
        raise ValueError(f"missing {keyword} section")

    start = text.find(opener, match.end())
    if start == -1:
        raise ValueError(f"missing {keyword} section opener")

    depth = 0
    for index in range(start, len(text)):
        character = text[index]
        if character == opener:
            depth += 1
        elif character == closer:
            depth -= 1
            if depth == 0:
                return text[start + 1 : index]

    raise ValueError(f"unterminated {keyword} section")


def _extract_named_blocks(section: str) -> set[str]:
    names: set[str] = set()
    index = 0
    while index < len(section):
        match = _IDENTIFIER_PATTERN.search(section, index)
        if match is None:
            break

        next_index = _skip_whitespace(section, match.end())
        if next_index < len(section) and section[next_index] == "{":
            names.add(match.group(0))
            index = _skip_block(section, next_index)
        else:
            index = match.end()

    if not names:
        raise ValueError("missing named boundary patches")
    return names


def _skip_block(text: str, start: int) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("unterminated named boundary patch")


def _skip_whitespace(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _mismatch_details(
    mesh_patches: set[str], field_patches: dict[Path, set[str]]
) -> dict[str, str]:
    details: dict[str, str] = {}
    for relative_path, patches in field_patches.items():
        missing_patches = mesh_patches - patches
        extra_patches = patches - mesh_patches
        if missing_patches:
            details[f"{relative_path.as_posix()}.missing_patches"] = _join_names(missing_patches)
        if extra_patches:
            details[f"{relative_path.as_posix()}.extra_patches"] = _join_names(extra_patches)
    return details


def _join_paths(paths: list[Path]) -> str:
    return ",".join(path.as_posix() for path in paths)


def _join_names(names: set[str] | list[str] | tuple[str, ...]) -> str:
    return ",".join(sorted(names))
