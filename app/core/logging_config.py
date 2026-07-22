import logging

from app.core.config import LOG_LEVEL
from app.core.request_id import get_request_id


class RequestIdLogFilter(logging.Filter):
    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()

    handler.addFilter(RequestIdLogFilter())

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s %(message)s"
    )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(LOG_LEVEL)
