from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_disposes_database_engine_on_shutdown() -> None:
    with patch(
        "app.core.lifespan.engine.dispose"
    ) as dispose:
        with TestClient(app) as client:
            response = client.get(
                "/health/live"
            )

            assert response.status_code == 200

        dispose.assert_called_once()
