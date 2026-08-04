import importlib.util
import json
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "ensure-homologation-reviewer.py"
)
SPEC = importlib.util.spec_from_file_location("ensure_homologation_reviewer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_adds_distinct_reviewer_without_changing_other_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.homologation"
    env_file.write_text(
        'APP_ENV=homologation\nADMIN_CREDENTIALS_JSON={"trainer":"A"}\n'
        "CLIENT_CREDENTIALS_JSON={}\n",
        encoding="utf-8",
    )

    count, changed = MODULE.ensure_reviewer(env_file)

    assert count == 2
    assert changed is True
    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "APP_ENV=homologation"
    credentials = json.loads(lines[1].split("=", 1)[1])
    assert credentials["trainer"] == "A"
    assert len(credentials["model-reviewer"]) >= 24
    assert credentials["model-reviewer"] != credentials["trainer"]

    second_count, second_changed = MODULE.ensure_reviewer(env_file)
    assert second_count == 2
    assert second_changed is False
