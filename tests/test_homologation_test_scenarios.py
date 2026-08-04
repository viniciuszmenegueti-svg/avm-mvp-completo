import importlib.util
from pathlib import Path
from types import ModuleType


def load_homologation_script() -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / "homologation-test.py"
    spec = importlib.util.spec_from_file_location("homologation_test_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rj_scenario_builds_consistent_order_and_shadow_dataset() -> None:
    module = load_homologation_script()

    order = module.build_order_payload("HOMOLOGATION-RJ-TEST", "rj")
    training = module.build_shadow_training_payload("SHADOW-TEST", "rj")

    assert order["property"]["state"] == "RJ"
    assert order["property"]["city"] == "Rio de Janeiro"
    assert order["property"]["city_ibge_code"] == "3304557"
    assert order["property"]["neighborhood"] == "Copacabana"
    assert order["location_confirmation"]["confirmation_method"] == (
        "HOMOLOGATION_TEST"
    )
    assert order["location_confirmation"]["evidence_reference"].endswith("-RJ")

    assert training["city_ibge_code"] == "3304557"
    assert training["dependent_variable"] == "usable_market_value_brl"
    assert training["dataset_metadata"]["contractual_use"] is False
    assert training["dataset_metadata"]["classification"] == (
        "SYNTHETIC_HOMOLOGATION_ONLY"
    )
    assert training["dataset_metadata"]["scenario"] == "RJ"
    assert len(training["observations"]) == len(training["values"]) == 48


def test_sp_remains_the_default_scenario() -> None:
    module = load_homologation_script()

    order = module.build_order_payload("HOMOLOGATION-SP-TEST")
    training = module.build_shadow_training_payload("SHADOW-TEST")

    assert order["property"]["state"] == "SP"
    assert order["property"]["city_ibge_code"] == "3550308"
    assert training["city_ibge_code"] == "3550308"
    assert training["dataset_metadata"]["scenario"] == "SP"


def test_reuses_only_the_matching_active_shadow_model() -> None:
    module = load_homologation_script()
    expected = {
        "model_id": "rj-shadow",
        "status": "HOMOLOGATION_APPROVED",
        "city_ibge_code": "3304557",
        "property_type": "APARTMENT",
        "dependent_variable": "usable_market_value_brl",
        "dataset_version": "SHADOW-SYNTHETIC-RJ-SHADOW-EXISTING",
        "contractual_validity": False,
    }
    listing = {
        "items": [
            {**expected, "city_ibge_code": "3550308"},
            {**expected, "status": "CANDIDATE"},
            expected,
        ]
    }

    assert module.find_active_shadow_model(listing, "rj") == expected
    assert module.find_active_shadow_model(listing, "sp") is None
