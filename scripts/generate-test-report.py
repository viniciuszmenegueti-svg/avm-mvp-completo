import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from app.schemas.order import (
    LocationConfirmationDeclaration,
    OrderResponse,
    OrderSlaOutcome,
    OrderStatus,
)
from app.schemas.property import PropertyInput, PropertyType
from app.schemas.valuation import (
    ValuationMethod,
    ValuationResponse,
)
from app.services.report_service import build_valuation_pdf


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera um relatório PDF demonstrativo sem acessar o banco de dados.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/pdf/relatorio-avm-teste-requisitos.pdf"),
        help="Caminho do arquivo PDF de saída.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    timestamp = datetime.now(timezone.utc)
    order = OrderResponse(
        internal_order_id="10000000-0000-4000-8000-000000000001",
        external_order_id="TESTE-REQUISITOS-20260731-0001",
        status=OrderStatus.COMPLETED,
        received_at=timestamp,
        response_deadline_at=timestamp + timedelta(seconds=300),
        responded_at=timestamp,
        response_elapsed_seconds=0,
        sla_outcome=OrderSlaOutcome.WITHIN_SLA,
        property=PropertyInput(
            property_type=PropertyType.APARTMENT,
            state="SP",
            city="São Paulo",
            city_ibge_code="3550308",
            postal_code="01001-000",
            neighborhood="Sé",
            street="Praça da Sé",
            number="100",
            complement="Apartamento demonstrativo 10",
            private_area_m2=70,
            built_area_m2=80,
            land_area_m2=None,
            bedrooms=2,
            bathrooms=2,
            parking_spaces=1,
        ),
        location_confirmation=LocationConfirmationDeclaration(
            is_confirmed=True,
            confirmation_method="TEST_DATASET_GEOCODING",
            evidence_reference="EVIDENCIA-GEOGRAFICA-DEMONSTRATIVA-0001",
            verified_by="PIPELINE-DE-TESTE-AVM",
            latitude=-23.550520,
            longitude=-46.633308,
            accuracy_meters=35,
        ),
    )
    valuation = ValuationResponse(
        valuation_id="20000000-0000-4000-8000-000000000001",
        internal_order_id=order.internal_order_id,
        method=ValuationMethod.RULE_BASED_V1,
        model_version="1.0.0-demo",
        estimated_value=Decimal("735000.00"),
        minimum_value=Decimal("661500.00"),
        maximum_value=Decimal("808500.00"),
        price_per_m2=Decimal("10500.00"),
        reference_area_m2=Decimal("70.00"),
        confidence_score=Decimal("0.8000"),
        factors={
            "area_factor": "1.0000",
            "base_price_per_m2": "10500.00",
            "characteristics_factor": "1.0000",
            "location_factor": "1.0000",
            "reference_area_m2": "70.00",
        },
        confidence_reasons=[
            "Preço-base disponível para município e tipologia.",
            "Área de referência válida.",
            "Quatro atributos complementares informados.",
        ],
        calculated_at=timestamp,
    )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(build_valuation_pdf(order, valuation))
    print(arguments.output.resolve())


if __name__ == "__main__":
    main()
