from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["Cockpit"])
STATIC_DIRECTORY = Path(__file__).resolve().parents[2] / "static"


@router.get(
    "/cockpit",
    include_in_schema=False,
)
def cockpit() -> FileResponse:
    return FileResponse(
        STATIC_DIRECTORY / "cockpit.html",
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            ),
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        },
    )
