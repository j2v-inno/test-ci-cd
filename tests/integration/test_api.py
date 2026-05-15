"""Integration tests run against a deployed instance.

Set TARGET_URL to point at the env under test (defaults to dev stack).
The QA stage in CI hits the dev environment on http://host.docker.internal:8001.
"""

from __future__ import annotations

import os
import time

import pytest
import requests

TARGET_URL = os.environ.get("TARGET_URL", "http://localhost:8001").rstrip("/")
TIMEOUT = 5


def _wait_for_ready(url: str, attempts: int = 30, delay: float = 1.0) -> None:
    for _ in range(attempts):
        try:
            r = requests.get(f"{url}/health", timeout=TIMEOUT)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(delay)
    pytest.fail(f"app at {url} never became healthy")


@pytest.fixture(scope="module", autouse=True)
def _ready():
    _wait_for_ready(TARGET_URL)


@pytest.mark.integration
def test_health_endpoint():
    r = requests.get(f"{TARGET_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.integration
def test_version_endpoint_reports_environment():
    r = requests.get(f"{TARGET_URL}/version", timeout=TIMEOUT)
    assert r.status_code == 200
    body = r.json()
    assert body["version"]
    assert body["environment"]


@pytest.mark.integration
def test_create_then_get_then_delete():
    created = requests.post(
        f"{TARGET_URL}/items",
        json={"name": "integration-widget", "price": 1.23},
        timeout=TIMEOUT,
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    fetched = requests.get(f"{TARGET_URL}/items/{item_id}", timeout=TIMEOUT)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "integration-widget"

    deleted = requests.delete(f"{TARGET_URL}/items/{item_id}", timeout=TIMEOUT)
    assert deleted.status_code == 204


@pytest.mark.integration
def test_validation_rejects_empty_name():
    r = requests.post(
        f"{TARGET_URL}/items",
        json={"name": "", "price": 1.0},
        timeout=TIMEOUT,
    )
    assert r.status_code == 400
