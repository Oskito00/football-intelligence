"""Legacy chat API entrypoint backed by the Football Intelligence API."""

from football_intelligence.api import Message, app, create_app

__all__ = ["Message", "app", "create_app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
