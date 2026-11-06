import pytest
from web_server import create_keep_alive_app

def test_keep_alive_endpoint_returns_health():
    app = create_keep_alive_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    assert b"Bot is running online!" in response.data
