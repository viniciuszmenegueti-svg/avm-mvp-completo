from unittest.mock import MagicMock, patch

import pytest

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
        mocked_session.rollback.assert_not_called()
        mocked_session.close.assert_not_called()

        with pytest.raises(StopIteration):
            next(dependency)

        mocked_session.rollback.assert_not_called()
        mocked_session.close.assert_called_once()


def test_database_session_rolls_back_and_closes_after_error() -> None:
    mocked_session = MagicMock()

    with patch(
        "app.infrastructure.dependencies.SessionLocal",
        return_value=mocked_session,
    ):
        dependency = get_database_session()

        returned_session = next(dependency)

        assert returned_session is mocked_session

        with pytest.raises(
            RuntimeError,
            match="Falha simulada durante a requisição",
        ):
            dependency.throw(RuntimeError("Falha simulada durante a requisição"))

        mocked_session.rollback.assert_called_once()
        mocked_session.close.assert_called_once()
