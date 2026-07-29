from pydantic import BaseModel, Field, model_validator


class StatisticalModelFitRequest(BaseModel):
    feature_names: list[str] = Field(min_length=1, max_length=20)
    observations: list[list[float]] = Field(min_length=3, max_length=10_000)
    values: list[float] = Field(min_length=3, max_length=10_000)
    target: list[float] = Field(min_length=1, max_length=20)
    expected_signs: dict[str, int] = Field(default_factory=dict)
    confidence_level: float = Field(default=0.80, gt=0, lt=1)

    @model_validator(mode="after")
    def validate_dimensions(self) -> "StatisticalModelFitRequest":
        width = len(self.feature_names)
        if len(set(self.feature_names)) != width:
            raise ValueError("feature_names must be unique.")
        if any(len(row) != width for row in self.observations):
            raise ValueError("Every observation must match feature_names.")
        if len(self.values) != len(self.observations):
            raise ValueError("One value is required per observation.")
        if len(self.target) != width:
            raise ValueError("target must match feature_names.")
        return self


class NBRGradeResponse(BaseModel):
    sample: str | None
    significance: str | None
    precision: str | None
    overall: str | None


class StatisticalModelFitResponse(BaseModel):
    feature_names: list[str]
    coefficients: list[float]
    coefficient_p_values: list[float]
    observation_count: int
    variable_count: int
    degrees_of_freedom: int
    r_squared: float
    adjusted_r_squared: float
    correlation_coefficient: float
    residual_standard_error: float
    press: float
    loocv_rmse: float
    maximum_regressor_p_value: float
    target_estimate: float
    confidence_level: float
    confidence_lower: float
    confidence_upper: float
    confidence_amplitude_percent: float
    grades: NBRGradeResponse
    economic_gates_passed: bool
    economic_gate_failures: list[str]
    homologated: bool = False
    review_notice: str
