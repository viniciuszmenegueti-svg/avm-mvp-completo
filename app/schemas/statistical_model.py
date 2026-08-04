from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


MarketFieldValue = str | int | float | bool | None


class MarketDatasetPolicyRequest(BaseModel):
    city_ibge_code: str = Field(pattern=r"^\d{7}$")
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=2)
    property_type: str = Field(min_length=3, max_length=30)
    reference_date: date
    variable_count: int = Field(ge=1, le=20)
    max_age_days: int = Field(default=365, ge=0, le=3650)
    max_location_accuracy_meters: float = Field(default=50.0, gt=0, le=50)
    max_source_share: float = Field(default=0.50, gt=0, le=1)
    required_features: list[str] = Field(
        default_factory=lambda: [
            "private_area_m2",
            "bedrooms",
            "bathrooms",
            "parking_spaces",
        ],
        min_length=1,
        max_length=20,
    )


class MarketDatasetAssessmentRequest(BaseModel):
    policy: MarketDatasetPolicyRequest
    observations: list[dict[str, MarketFieldValue]] = Field(
        min_length=1,
        max_length=10_000,
    )


class MarketObservationAssessmentResponse(BaseModel):
    observation_id: str
    collection_valid: bool
    model_eligible: bool
    reason_codes: list[str]
    duplicate_of: str | None
    price_per_m2_brl: float | None
    source_fingerprint: str


class MarketDatasetAssessmentResponse(BaseModel):
    total_count: int
    collection_valid_count: int
    model_eligible_count: int
    excluded_count: int
    source_counts: dict[str, int]
    maximum_source_share: float | None
    source_distribution_passed: bool
    sample_grade: str | None
    required_sample_sizes: dict[str, int]
    dataset_sha256: str
    model_ready: bool
    assessments: list[MarketObservationAssessmentResponse]


class StatisticalModelFitRequest(BaseModel):
    feature_names: list[str] = Field(min_length=1, max_length=20)
    observations: list[list[float]] = Field(min_length=3, max_length=10_000)
    values: list[float] = Field(min_length=3, max_length=10_000)
    target: list[float] = Field(min_length=1, max_length=20)
    expected_signs: dict[str, int] = Field(default_factory=dict)
    confidence_level: float = Field(default=0.8, ge=0.8, le=0.8)

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
    model_significance: str | None
    precision: str | None
    automatic_fundamentation_gate: str | None
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
    f_statistic: float
    model_p_value: float
    variance_inflation_factors: dict[str, float]
    maximum_vif: float
    normality_test: str
    normality_p_value: float
    breusch_pagan_statistic: float
    breusch_pagan_p_value: float
    durbin_watson: float
    maximum_standardized_residual: float
    maximum_cooks_distance: float
    feature_ranges: dict[str, tuple[float, float]]
    target_estimate: float
    confidence_level: float
    confidence_lower: float
    confidence_upper: float
    confidence_amplitude_percent: float
    grades: NBRGradeResponse
    economic_gates_passed: bool
    economic_gate_failures: list[str]
    homologated: bool = False
    full_nbr_compliance_claimed: bool = False
    review_notice: str


class StatisticalDatasetStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    HOMOLOGATION_APPROVED = "HOMOLOGATION_APPROVED"
    CONTRACTUAL_APPROVED = "CONTRACTUAL_APPROVED"
    REJECTED = "REJECTED"


class StatisticalModelStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    HOMOLOGATION_APPROVED = "HOMOLOGATION_APPROVED"
    CONTRACTUAL_ACTIVE = "CONTRACTUAL_ACTIVE"
    REJECTED = "REJECTED"
    DISABLED = "DISABLED"


class StatisticalModelTrainRequest(StatisticalModelFitRequest):
    city_ibge_code: str = Field(pattern=r"^\d{7}$")
    property_type: str = Field(pattern=r"^(APARTMENT|HOUSE|LAND)$")
    dataset_version: str = Field(min_length=3, max_length=80)
    dataset_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-fA-F0-9]{64}$",
        description=(
            "Hash opcional para conferência. Quando informado, deve coincidir "
            "com o hash calculado pelo servidor sobre a matriz e sua semântica."
        ),
    )
    source_reference: str = Field(min_length=3, max_length=500)
    reference_date: date
    model_version: str = Field(min_length=1, max_length=50)
    valid_from: date
    valid_until: date | None = None
    dataset_metadata: dict[str, MarketFieldValue] = Field(default_factory=dict)
    dependent_variable: Literal[
        "usable_market_value_brl",
        "asking_price_brl",
    ]
    dependent_variable_unit: Literal["BRL"] = "BRL"
    dependent_variable_transformation: Literal["NONE"] = "NONE"
    feature_transformations: dict[str, Literal["NONE"]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_validity(self) -> "StatisticalModelTrainRequest":
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("valid_until must not precede valid_from.")
        supported_by_type = {
            "APARTMENT": {
                "private_area_m2",
                "built_area_m2",
                "bedrooms",
                "bathrooms",
                "parking_spaces",
            },
            "HOUSE": {
                "built_area_m2",
                "land_area_m2",
                "bedrooms",
                "bathrooms",
                "parking_spaces",
            },
            "LAND": {"land_area_m2"},
        }
        required_reference_area = {
            "APARTMENT": "private_area_m2",
            "HOUSE": "built_area_m2",
            "LAND": "land_area_m2",
        }
        allowed = supported_by_type[self.property_type]
        unsupported = sorted(set(self.feature_names) - allowed)
        if unsupported:
            raise ValueError(
                "Features unsupported for property_type: " + ", ".join(unsupported)
            )
        if required_reference_area[self.property_type] not in self.feature_names:
            raise ValueError(
                "The reference-area feature is required for the selected property_type."
            )
        if set(self.expected_signs) != set(self.feature_names):
            raise ValueError(
                "expected_signs must explicitly cover every feature in the model."
            )
        if any(sign not in {-1, 1} for sign in self.expected_signs.values()):
            raise ValueError("Expected signs must be either -1 or 1.")
        if self.dependent_variable == "asking_price_brl":
            classification = str(
                self.dataset_metadata.get("training_classification", "")
            ).upper()
            model_ready = self.dataset_metadata.get("market_dataset_model_ready")
            if classification != "RESEARCH_ONLY" or model_ready is not False:
                raise ValueError(
                    "asking_price_brl is accepted only for an explicitly "
                    "RESEARCH_ONLY dataset with market_dataset_model_ready=false."
                )
        if set(self.feature_transformations) - set(self.feature_names):
            raise ValueError("feature_transformations references an unknown feature.")
        for index, target_value in enumerate(self.target):
            values = [row[index] for row in self.observations]
            if target_value < min(values) or target_value > max(values):
                raise ValueError(
                    "Training diagnostic target extrapolates "
                    f"{self.feature_names[index]}."
                )
        return self


class StatisticalModelApprovalRequest(BaseModel):
    approval_reference: str = Field(min_length=3, max_length=250)


class StatisticalModelRecordResponse(BaseModel):
    model_id: str
    dataset_id: str
    city_ibge_code: str
    property_type: str
    method: str
    model_version: str
    status: StatisticalModelStatus
    dataset_status: StatisticalDatasetStatus
    dataset_version: str
    dataset_sha256: str
    training_matrix_sha256: str
    artifact_sha256: str
    feature_names: list[str]
    coefficients: list[float]
    diagnostics: dict[str, object]
    dependent_variable: str
    dependent_variable_unit: str
    dependent_variable_transformation: str
    feature_ranges: dict[str, tuple[float, float]]
    valid_from: date
    valid_until: date | None
    trained_by: str
    trained_at: datetime
    approved_by: str | None
    approval_reference: str | None
    approved_at: datetime | None
    contractual_validity: bool = False


class StatisticalModelListResponse(BaseModel):
    total: int = Field(ge=0)
    items: list[StatisticalModelRecordResponse]
