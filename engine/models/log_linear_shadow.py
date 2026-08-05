"""Preditor isolado para o modelo log-linear de homologação sombra."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_FEATURE_NAMES = (
    "intercept",
    "log_private_area_m2",
    "bedrooms",
    "bathrooms",
    "parking_spaces",
    "neighborhood_botafogo",
    "botafogo_x_log_area",
)


class ShadowModelError(ValueError):
    """Erro de configuração, domínio ou cálculo do modelo sombra."""


@dataclass(frozen=True, slots=True)
class ShadowModel:
    name: str
    version: str
    city_ibge_code: str
    property_type: str
    supported_neighborhoods: tuple[str, ...]
    value_basis: str
    artifact_sha256: str
    coefficients: tuple[float, ...]
    smearing_factor: float
    interval_log_radius: float
    input_domain: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class ShadowPrediction:
    estimated_value_brl: float
    confidence_lower_brl: float
    confidence_upper_brl: float
    confidence_level: float
    confidence_amplitude_percent: float
    price_per_m2_brl: float
    artifact_sha256: str
    model_name: str
    model_version: str
    execution_mode: str
    value_basis: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ShadowModelError(f"Arquivo não encontrado: {path}")

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8-sig")
        )
    except json.JSONDecodeError as error:
        raise ShadowModelError(
            f"JSON inválido: {path}"
        ) from error

    if not isinstance(payload, dict):
        raise ShadowModelError(
            f"O conteúdo deve ser um objeto JSON: {path}"
        )

    return payload


def _absolute_path(
    raw_path: str,
    *,
    project_root: Path,
) -> Path:
    path = Path(raw_path)

    if not path.is_absolute():
        path = project_root / path

    return path.resolve()


def _domain_from_config(
    config: dict[str, Any],
) -> dict[str, tuple[float, float]]:
    raw_domain = config.get("input_domain")

    if not isinstance(raw_domain, dict):
        raise ShadowModelError(
            "A configuração não possui input_domain."
        )

    required = (
        "private_area_m2",
        "bedrooms",
        "bathrooms",
        "parking_spaces",
    )

    parsed: dict[str, tuple[float, float]] = {}

    for field in required:
        bounds = raw_domain.get(field)

        if not isinstance(bounds, dict):
            raise ShadowModelError(
                f"Domínio ausente para {field}."
            )

        try:
            minimum = float(bounds["minimum"])
            maximum = float(bounds["maximum"])
        except (KeyError, TypeError, ValueError) as error:
            raise ShadowModelError(
                f"Domínio inválido para {field}."
            ) from error

        if not math.isfinite(minimum) or not math.isfinite(maximum):
            raise ShadowModelError(
                f"Domínio não finito para {field}."
            )

        if minimum > maximum:
            raise ShadowModelError(
                f"Domínio invertido para {field}."
            )

        parsed[field] = (minimum, maximum)

    return parsed


def load_shadow_model(
    config_path: Path,
    *,
    project_root: Path | None = None,
) -> ShadowModel:
    config_path = config_path.resolve()

    if project_root is None:
        project_root = config_path.parent.parent

    project_root = project_root.resolve()
    config = _read_json(config_path)

    if config.get("enabled") is not True:
        raise ShadowModelError(
            "O modelo sombra está desabilitado."
        )

    if config.get("operating_mode") != "SHADOW":
        raise ShadowModelError(
            "A configuração não está em modo SHADOW."
        )

    if config.get("formal_homologation") is not False:
        raise ShadowModelError(
            "O modelo sombra não pode declarar homologação formal."
        )

    artifact_raw_path = config.get("artifact_path")

    if not isinstance(artifact_raw_path, str) or not artifact_raw_path.strip():
        raise ShadowModelError(
            "artifact_path não foi informado."
        )

    artifact_path = _absolute_path(
        artifact_raw_path,
        project_root=project_root,
    )

    artifact = _read_json(artifact_path)
    artifact_sha256 = _sha256_file(artifact_path)

    feature_names = artifact.get("feature_names")

    if tuple(feature_names or ()) != EXPECTED_FEATURE_NAMES:
        raise ShadowModelError(
            "As variáveis do artefato não correspondem ao modelo v3."
        )

    coefficients_raw = artifact.get("coefficients")

    if not isinstance(coefficients_raw, list):
        raise ShadowModelError(
            "Coeficientes ausentes no artefato."
        )

    try:
        coefficients = tuple(
            float(value)
            for value in coefficients_raw
        )
    except (TypeError, ValueError) as error:
        raise ShadowModelError(
            "Coeficientes inválidos no artefato."
        ) from error

    if len(coefficients) != len(EXPECTED_FEATURE_NAMES):
        raise ShadowModelError(
            "Quantidade de coeficientes incompatível."
        )

    if not all(math.isfinite(value) for value in coefficients):
        raise ShadowModelError(
            "O artefato contém coeficiente não finito."
        )

    try:
        smearing_factor = float(
            artifact["smearing_factor"]
        )
        interval_log_radius = float(
            artifact["interval_log_radius"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ShadowModelError(
            "Parâmetros log-lineares ausentes ou inválidos."
        ) from error

    if smearing_factor <= 0 or not math.isfinite(smearing_factor):
        raise ShadowModelError(
            "smearing_factor deve ser positivo e finito."
        )

    if interval_log_radius <= 0 or not math.isfinite(
        interval_log_radius
    ):
        raise ShadowModelError(
            "interval_log_radius deve ser positivo e finito."
        )

    supported_neighborhoods_raw = config.get(
        "supported_neighborhoods"
    )

    if not isinstance(supported_neighborhoods_raw, list):
        raise ShadowModelError(
            "supported_neighborhoods deve ser uma lista."
        )

    supported_neighborhoods = tuple(
        str(value).strip()
        for value in supported_neighborhoods_raw
        if str(value).strip()
    )

    if set(supported_neighborhoods) != {
        "Botafogo",
        "Copacabana",
    }:
        raise ShadowModelError(
            "O modelo v3 suporta somente Botafogo e Copacabana."
        )

    return ShadowModel(
        name=str(config.get("model_name", "")).strip(),
        version=str(config.get("model_version", "")).strip(),
        city_ibge_code=str(
            config.get("city_ibge_code", "")
        ).strip(),
        property_type=str(
            config.get("property_type", "")
        ).strip(),
        supported_neighborhoods=supported_neighborhoods,
        value_basis=str(
            config.get("value_basis", "")
        ).strip(),
        artifact_sha256=artifact_sha256,
        coefficients=coefficients,
        smearing_factor=smearing_factor,
        interval_log_radius=interval_log_radius,
        input_domain=_domain_from_config(config),
    )


def _validate_domain(
    model: ShadowModel,
    *,
    private_area_m2: float,
    bedrooms: float,
    bathrooms: float,
    parking_spaces: float,
) -> None:
    inputs = {
        "private_area_m2": private_area_m2,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parking_spaces": parking_spaces,
    }

    for name, value in inputs.items():
        if not math.isfinite(value):
            raise ShadowModelError(
                f"{name} deve ser finito."
            )

        minimum, maximum = model.input_domain[name]

        if value < minimum or value > maximum:
            raise ShadowModelError(
                f"Extrapolação bloqueada para {name}: "
                f"{value:g} fora de [{minimum:g}, {maximum:g}]."
            )


def predict_shadow_model(
    model: ShadowModel,
    *,
    city_ibge_code: str,
    property_type: str,
    neighborhood: str,
    private_area_m2: float,
    bedrooms: float,
    bathrooms: float,
    parking_spaces: float,
) -> ShadowPrediction:
    if city_ibge_code != model.city_ibge_code:
        raise ShadowModelError(
            "Cidade fora do domínio do modelo sombra."
        )

    if property_type != model.property_type:
        raise ShadowModelError(
            "Tipologia fora do domínio do modelo sombra."
        )

    neighborhood = neighborhood.strip()

    if neighborhood not in model.supported_neighborhoods:
        raise ShadowModelError(
            "Bairro fora do domínio do modelo sombra."
        )

    _validate_domain(
        model,
        private_area_m2=float(private_area_m2),
        bedrooms=float(bedrooms),
        bathrooms=float(bathrooms),
        parking_spaces=float(parking_spaces),
    )

    area = float(private_area_m2)
    log_area = math.log(area)
    botafogo = 1.0 if neighborhood == "Botafogo" else 0.0

    features = (
        1.0,
        log_area,
        float(bedrooms),
        float(bathrooms),
        float(parking_spaces),
        botafogo,
        botafogo * log_area,
    )

    predicted_log = sum(
        coefficient * feature
        for coefficient, feature in zip(
            model.coefficients,
            features,
            strict=True,
        )
    )

    estimate = (
        math.exp(predicted_log) *
        model.smearing_factor
    )

    lower = estimate * math.exp(
        -model.interval_log_radius
    )
    upper = estimate * math.exp(
        model.interval_log_radius
    )

    if estimate <= 0 or lower <= 0 or upper <= lower:
        raise ShadowModelError(
            "O modelo produziu valores inválidos."
        )

    amplitude_percent = (
        (upper - lower) /
        estimate
    ) * 100.0

    return ShadowPrediction(
        estimated_value_brl=estimate,
        confidence_lower_brl=lower,
        confidence_upper_brl=upper,
        confidence_level=0.80,
        confidence_amplitude_percent=amplitude_percent,
        price_per_m2_brl=estimate / area,
        artifact_sha256=model.artifact_sha256,
        model_name=model.name,
        model_version=model.version,
        execution_mode="SHADOW",
        value_basis=model.value_basis,
    )
