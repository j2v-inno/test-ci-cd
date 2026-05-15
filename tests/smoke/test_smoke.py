"""Smoke tests = a couple of checks that prove the deploy is alive.

Used as the post-deploy gate in every environment (dev/staging/prod).
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


@pytest.mark.smoke
def test_health_ok():
    r = requests.get(f"{TARGET_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200


@pytest.mark.smoke
def test_version_reachable():
    r = requests.get(f"{TARGET_URL}/version", timeout=TIMEOUT)
    assert r.status_code == 200
    assert "version" in r.json()
