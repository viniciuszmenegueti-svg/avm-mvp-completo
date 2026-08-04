from pathlib import Path

from app.core import config


def test_dotenv_loader_preserves_existing_environment_precedence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    variable_name = "AVM_CONFIG_PRECEDENCE_TEST"
    env_file = tmp_path / ".env"
    env_file.write_text(f"{variable_name}=from-file\n", encoding="utf-8")
    monkeypatch.setenv(variable_name, "from-process")

    config._load_project_environment(env_file)

    assert config.os.environ[variable_name] == "from-process"


def test_dotenv_loader_supplies_missing_environment_value(
    monkeypatch,
    tmp_path: Path,
) -> None:
    variable_name = "AVM_CONFIG_FILE_TEST"
    env_file = tmp_path / ".env"
    env_file.write_text(f"{variable_name}=from-file\n", encoding="utf-8")
    monkeypatch.delenv(variable_name, raising=False)

    config._load_project_environment(env_file)

    assert config.os.environ[variable_name] == "from-file"
