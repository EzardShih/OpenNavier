from pathlib import Path
from shutil import rmtree


class CasePathNotEmptyError(ValueError):
    """Raised when a case template would overwrite existing user files."""


def create_cavity_case(case_path: Path | str, *, force: bool = False) -> Path:
    return _create_case(case_path, template_files=CAVITY_TEMPLATE_FILES, force=force)


def create_duct_pressure_drop_case(case_path: Path | str, *, force: bool = False) -> Path:
    return _create_case(case_path, template_files=DUCT_PRESSURE_DROP_TEMPLATE_FILES, force=force)


def _create_case(
    case_path: Path | str,
    *,
    template_files: dict[Path, str],
    force: bool = False,
) -> Path:
    root = Path(case_path)
    if root.exists() and not root.is_dir():
        raise CasePathNotEmptyError(f"Refusing to overwrite existing path: {root}")
    elif root.exists() and force and _is_protected_path(root.resolve()):
        raise CasePathNotEmptyError(f"Refusing to force-overwrite protected path: {root}")
    elif root.exists() and any(root.iterdir()):
        if not force:
            raise CasePathNotEmptyError(f"Refusing to overwrite non-empty path: {root}")
        _validate_force_target(root, template_files=template_files)
        rmtree(root)

    for directory in ["0", "constant", "system"]:
        (root / directory).mkdir(parents=True, exist_ok=True)

    for relative_path, content in template_files.items():
        (root / relative_path).write_text(content, encoding="utf-8", newline="\n")

    return root


def _validate_force_target(root: Path, *, template_files: dict[Path, str]) -> None:
    resolved_root = root.resolve()
    if _is_protected_path(resolved_root):
        raise CasePathNotEmptyError(f"Refusing to force-overwrite protected path: {root}")
    if not _is_generated_case(root, template_files=template_files):
        raise CasePathNotEmptyError(
            f"Refusing to force-overwrite unknown non-empty path: {root}"
        )


def _is_protected_path(resolved_root: Path) -> bool:
    cwd = Path.cwd().resolve()
    protected_paths = {cwd, *cwd.parents, Path.home().resolve()}
    if resolved_root.anchor:
        protected_paths.add(Path(resolved_root.anchor).resolve())
    return resolved_root in protected_paths


def _is_generated_case(root: Path, *, template_files: dict[Path, str]) -> bool:
    expected_files = set(template_files)
    observed_files = {path.relative_to(root) for path in root.rglob("*") if path.is_file()}
    if observed_files != expected_files:
        return False

    return all(
        (root / relative_path).read_text(encoding="utf-8") == content
        for relative_path, content in template_files.items()
    )


def _foam_dictionary(*, name: str, class_name: str, location: str, body: str) -> str:
    return (
        "FoamFile\n"
        "{\n"
        "    version     2.0;\n"
        "    format      ascii;\n"
        f"    class       {class_name};\n"
        f'    location    "{location}";\n'
        f"    object      {name};\n"
        "}\n"
        "\n"
        f"{body.strip()}\n"
    )


CAVITY_TEMPLATE_FILES = {
    Path("0") / "U": _foam_dictionary(
        name="U",
        class_name="volVectorField",
        location="0",
        body="""
dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    movingWall
    {
        type            fixedValue;
        value           uniform (1 0 0);
    }

    fixedWalls
    {
        type            noSlip;
    }

    frontAndBack
    {
        type            empty;
    }
}
""",
    ),
    Path("0") / "p": _foam_dictionary(
        name="p",
        class_name="volScalarField",
        location="0",
        body="""
dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    movingWall
    {
        type            zeroGradient;
    }

    fixedWalls
    {
        type            zeroGradient;
    }

    frontAndBack
    {
        type            empty;
    }
}
""",
    ),
    Path("constant") / "transportProperties": _foam_dictionary(
        name="transportProperties",
        class_name="dictionary",
        location="constant",
        body="""
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] 0.01;
""",
    ),
    Path("system") / "blockMeshDict": _foam_dictionary(
        name="blockMeshDict",
        class_name="dictionary",
        location="system",
        body="""
convertToMeters 1;

vertices
(
    (0 0 0)
    (1 0 0)
    (1 1 0)
    (0 1 0)
    (0 0 0.1)
    (1 0 0.1)
    (1 1 0.1)
    (0 1 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (20 20 1) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    movingWall
    {
        type wall;
        faces
        (
            (3 7 6 2)
        );
    }

    fixedWalls
    {
        type wall;
        faces
        (
            (0 4 7 3)
            (2 6 5 1)
            (1 5 4 0)
        );
    }

    frontAndBack
    {
        type empty;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }
);

mergePatchPairs
(
);
""",
    ),
    Path("system") / "controlDict": _foam_dictionary(
        name="controlDict",
        class_name="dictionary",
        location="system",
        body="""
application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         0.5;
deltaT          0.005;
writeControl    timeStep;
writeInterval   20;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
""",
    ),
    Path("system") / "fvSchemes": _foam_dictionary(
        name="fvSchemes",
        class_name="dictionary",
        location="system",
        body="""
ddtSchemes
{
    default         Euler;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear orthogonal;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         orthogonal;
}
""",
    ),
    Path("system") / "fvSolution": _foam_dictionary(
        name="fvSolution",
        class_name="dictionary",
        location="system",
        body="""
solvers
{
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-06;
        relTol          0.05;
    }

    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0;
    }
}

PISO
{
    nCorrectors     2;
    nNonOrthogonalCorrectors 0;
    pRefCell        0;
    pRefValue       0;
}
""",
    ),
}


DUCT_PRESSURE_DROP_TEMPLATE_FILES = {
    Path("0") / "U": _foam_dictionary(
        name="U",
        class_name="volVectorField",
        location="0",
        body="""
dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (10 0 0);

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (10 0 0);
    }

    outlet
    {
        type            zeroGradient;
    }

    walls
    {
        type            noSlip;
    }
}
""",
    ),
    Path("0") / "p": _foam_dictionary(
        name="p",
        class_name="volScalarField",
        location="0",
        body="""
dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }

    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }

    walls
    {
        type            zeroGradient;
    }
}
""",
    ),
    Path("constant") / "transportProperties": _foam_dictionary(
        name="transportProperties",
        class_name="dictionary",
        location="constant",
        body="""
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] 1.5e-05;
""",
    ),
    Path("constant") / "turbulenceProperties": _foam_dictionary(
        name="turbulenceProperties",
        class_name="dictionary",
        location="constant",
        body="""
simulationType  laminar;
""",
    ),
    Path("system") / "blockMeshDict": _foam_dictionary(
        name="blockMeshDict",
        class_name="dictionary",
        location="system",
        body="""
convertToMeters 1;

vertices
(
    (0 0 0)
    (1 0 0)
    (1 0.1 0)
    (0 0.1 0)
    (0 0 0.1)
    (1 0 0.1)
    (1 0.1 0.1)
    (0 0.1 0.1)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (40 4 4) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }

    outlet
    {
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }

    walls
    {
        type wall;
        faces
        (
            (0 1 5 4)
            (3 7 6 2)
            (0 3 2 1)
            (4 5 6 7)
        );
    }
);

mergePatchPairs
(
);
""",
    ),
    Path("system") / "controlDict": _foam_dictionary(
        name="controlDict",
        class_name="dictionary",
        location="system",
        body="""
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    timeStep;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
""",
    ),
    Path("system") / "fvSchemes": _foam_dictionary(
        name="fvSchemes",
        class_name="dictionary",
        location="system",
        body="""
ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss upwind;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}
""",
    ),
    Path("system") / "fvSolution": _foam_dictionary(
        name="fvSolution",
        class_name="dictionary",
        location="system",
        body="""
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }

    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
    pRefCell        0;
    pRefValue       0;
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
    }
}
""",
    ),
}
