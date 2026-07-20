import logging

from app.core.logging_config import (
    RequestIdLogFilter,
)
from app.core.request_id import request_id_context


def test_log_filter_adds_default_request_id() -> None:
    record = logging.LogRecord(
        name="avm-api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Mensagem de teste",
        args=(),
        exc_info=None,
    )

    log_filter = RequestIdLogFilter()

    assert log_filter.filter(record)
    assert record.request_id == "-"


def test_log_filter_adds_current_request_id() -> None:
    token = request_id_context.set(
        "logging-request-001"
    )

    try:
        record = logging.LogRecord(
            name="avm-api",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Mensagem de teste",
            args=(),
            exc_info=None,
        )

        log_filter = RequestIdLogFilter()

        assert log_filter.filter(record)
        assert record.request_id == (
            "logging-request-001"
        )

    finally:
        request_id_context.reset(token)
