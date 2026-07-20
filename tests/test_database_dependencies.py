from unittest.mock import MagicMock, patch

from app.infrastructure.dependencies import (
    get_database_session,
)


def test_database_session_is_closed() -> None:
    mocked_session = MagicMock()

    with patch(
        "app.infrastructure.dependencies.SessionLocal",
        return_value=mocked_session,
    ):
        dependency = get_database_session()

        returned_session = next(dependency)

        assert returned_session is mocked_session
        mocked_session.close.assert_not_called()

        try:
            next(dependency)
        except StopIteration:
            pass

        mocked_session.close.assert_called_once()


def test_database_session_closes_after_error() -> None:
    mocked_session = MagicMock()

    with patch(
        "app.infrastructure.dependencies.SessionLocal",
        return_value=mocked_session,
    ):
        dependency = get_database_session()

        next(dependency)

        try:
            dependency.throw(
                RuntimeError(
                    "Falha simulada durante a requisição"
                )
            )
        except RuntimeError:
            pass

        mocked_session.close.assert_called_once()
