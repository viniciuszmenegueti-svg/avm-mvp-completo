from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, filename: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / filename
    )
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


PREPARE = load_script(
    "prepare_market_training_observations",
    "prepare-market-training-observations.py",
)
REGISTER = load_script(
    "register_market_training_observation",
    "register-market-training-observation.py",
)


def test_planned_portal_does_not_depend_on_the_collected_source() -> None:
    assert PREPARE.planned_portal(1) == "ZAP_IMOVEIS"
    assert PREPARE.planned_portal(5) == "OLX"
    assert PREPARE.planned_portal(10) == "IMOVELWEB"


def test_planned_portal_rejects_an_invalid_sequence() -> None:
    with pytest.raises(ValueError, match="fora do plano"):
        PREPARE.planned_portal(0)


def test_registration_preserves_the_preferred_portal() -> None:
    queue_row: dict[str, object] = {
        "preferred_portal": "ZAP_IMOVEIS",
        "source_url": "",
        "asking_price_brl": "",
        "status": "PREPARED_PENDING_COLLECTION",
    }

    REGISTER.update_queue_registration(
        queue_row,
        source_url="https://example.test/listing/1",
        asking_price_brl="500000",
        status="PENDING_DATA_COMPLETENESS",
    )

    assert queue_row == {
        "preferred_portal": "ZAP_IMOVEIS",
        "source_url": "https://example.test/listing/1",
        "asking_price_brl": "500000",
        "status": "PENDING_DATA_COMPLETENESS",
    }
