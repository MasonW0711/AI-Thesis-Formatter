from __future__ import annotations

import threading
import webbrowser

import uvicorn

from app.core.config import settings


def open_browser() -> None:
    webbrowser.open(f"http://{settings.host}:{settings.port}")


if __name__ == "__main__":
    timer = threading.Timer(1.2, open_browser)
    timer.daemon = True
    timer.start()

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
