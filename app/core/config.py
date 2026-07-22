import os


APP_NAME = os.getenv(
    "APP_NAME",
    "AVM Imóveis API",
)

APP_VERSION = os.getenv(
    "APP_VERSION",
    "0.1.0",
)

APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    "Plataforma local para automação de avaliações e precificação de imóveis.",
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
