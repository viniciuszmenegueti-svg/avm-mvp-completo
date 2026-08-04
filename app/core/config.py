import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_project_environment(
    env_file: Path = PROJECT_ROOT / ".env",
) -> None:
    """Load local defaults without replacing process/container variables."""
    load_dotenv(
        dotenv_path=env_file,
        override=False,
    )


_load_project_environment()


APP_NAME = os.getenv(
    "APP_NAME",
    "AVM Imóveis API",
)

APP_VERSION = os.getenv(
    "APP_VERSION",
    "0.3.1",
)

APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    ("Plataforma local para automação de avaliações e precificação de imóveis."),
)

APP_ENV = os.getenv(
    "APP_ENV",
    "development",
)

APP_DEBUG = os.getenv(
    "APP_DEBUG",
    "false",
).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()

ADMIN_CREDENTIALS_JSON = os.getenv(
    "ADMIN_CREDENTIALS_JSON",
    "",
).strip()

ADMIN_API_KEY = os.getenv(
    "ADMIN_API_KEY",
    "",
)

ADMIN_ACTOR = os.getenv(
    "ADMIN_ACTOR",
    "",
).strip()

CLIENT_CREDENTIALS_JSON = os.getenv(
    "CLIENT_CREDENTIALS_JSON",
    "",
).strip()


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


# Proteção contratual: o modelo RULE_BASED_V1 usa preços-base demonstrativos.
# Ele só pode calcular quando esta flag estiver explicitamente habilitada.
ALLOW_SYNTHETIC_PRICING = _env_flag("ALLOW_SYNTHETIC_PRICING", "false")

# Modos de execução são separados para impedir que um resultado de teste seja
# promovido implicitamente a entrega contratual.
MODEL_EXECUTION_MODE = (
    os.getenv(
        "MODEL_EXECUTION_MODE",
        "DEMONSTRATION",
    )
    .strip()
    .upper()
)
