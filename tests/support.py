"""Shared helpers for the control service tests."""

import json

from desalplant.config import Config
from desalplant.console.http import Request, Response


def build(config: Config):
    """Build the whole service from a configuration."""
    from desalplant.app import build_application

    return build_application(config)


def call(console, method: str, path: str, body=None) -> Response:
    """Dispatch a request through the console."""
    text = "" if body is None else json.dumps(body)
    return console.handle(Request.parse(method, path, text))


def ok(console, method: str, path: str, body=None):
    """Dispatch a request and require a 200 response."""
    response = call(console, method, path, body)
    assert response.status == 200, response.body
    return response.body


def refused(console, method: str, path: str, body=None) -> Response:
    """Dispatch a request and require a refusal."""
    response = call(console, method, path, body)
    assert response.status >= 400, response.body
    return response
