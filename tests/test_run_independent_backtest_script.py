from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_script_module() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "run-independent-backtest.py"
    )
    specification = importlib.util.spec_from_file_location(
        "run_independent_backtest", script_path
    )
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_limitations_report_the_actual_observation_count() -> None:
    module = load_script_module()

    limitations = module.build_limitations(2)

    assert "2 observacoes" in limitations[0]
    assert "apenas uma observacao" not in " ".join(limitations)
