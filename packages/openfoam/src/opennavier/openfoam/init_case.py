from pathlib import Path
from shutil import rmtree


class CasePathNotEmptyError(ValueError):
    """Raised when a case template would overwrite existing user files."""


def create_cavity_case(case_path: Path | str, *, force: bool = False) -> Path:
    root = Path(case_path)
    if root.exists() and not root.is_dir():
        if not force:
            raise CasePathNotEmptyError(f"Refusing to overwrite existing path: {root}")
        root.unlink()
    elif root.exists() and any(root.iterdir()):
        if not force:
            raise CasePathNotEmptyError(f"Refusing to overwrite non-empty path: {root}")
        rmtree(root)

    for directory in ["0", "constant", "system"]:
        (root / directory).mkdir(parents=True, exist_ok=True)

    for relative_path, content in CAVITY_TEMPLATE_FILES.items():
        (root / relative_path).write_text(content, encoding="utf-8", newline="\n")

    return root


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
