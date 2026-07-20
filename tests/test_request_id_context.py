from app.core.request_id import (
    get_request_id,
    request_id_context,
)


def test_request_id_context_has_default_value() -> None:
    assert get_request_id() == "-"


def test_get_request_id_returns_current_context_value() -> None:
    token = request_id_context.set("request-context-test-001")

    try:
        assert get_request_id() == ("request-context-test-001")
    finally:
        request_id_context.reset(token)

    assert get_request_id() == "-"
