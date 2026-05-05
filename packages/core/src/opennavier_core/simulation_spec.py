from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, model_validator


class SimulationSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeometryDimensions(SimulationSpecModel):
    length: PositiveFloat
    width: PositiveFloat
    height: PositiveFloat


class GeometrySpec(SimulationSpecModel):
    kind: Literal["cavity"]
    dimensions: GeometryDimensions


class MeshCells(SimulationSpecModel):
    x: PositiveInt
    y: PositiveInt
    z: PositiveInt


class MeshSpec(SimulationSpecModel):
    kind: Literal["structured"]
    cells: MeshCells


class FluidSpec(SimulationSpecModel):
    density: PositiveFloat
    kinematic_viscosity: PositiveFloat


class BoundaryConditionSpec(SimulationSpecModel):
    patch: str
    field: Literal["U", "p"]
    kind: Literal["fixedValue", "noSlip", "empty", "zeroGradient"]
    value: float | list[float] | None = None

    @model_validator(mode="after")
    def validate_field_kind_value(self) -> Self:
        if self.field == "U":
            if self.kind == "fixedValue":
                if not isinstance(self.value, list) or len(self.value) != 3:
                    raise ValueError("U fixedValue requires a three-component vector value")
            elif self.value is not None:
                raise ValueError(f"U {self.kind} must not include a value")
        elif self.kind == "noSlip":
            raise ValueError("p noSlip is not a supported boundary condition")
        elif self.kind == "fixedValue":
            if not isinstance(self.value, float):
                raise ValueError("p fixedValue requires a scalar value")
        elif self.value is not None:
            raise ValueError(f"p {self.kind} must not include a value")

        return self


class RunControlSpec(SimulationSpecModel):
    start_time: float = 0.0
    end_time: PositiveFloat
    time_step: PositiveFloat
    write_interval: PositiveFloat

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class SimulationSpec(SimulationSpecModel):
    case_name: str
    solver_family: Literal["incompressible_laminar"]
    geometry: GeometrySpec
    mesh: MeshSpec
    fluid: FluidSpec
    boundary_conditions: list[BoundaryConditionSpec] = Field(min_length=1)
    run_control: RunControlSpec
