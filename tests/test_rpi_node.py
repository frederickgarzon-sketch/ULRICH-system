import os

os.environ["RPI_MOCK_MODE"] = "true"

from fastapi.testclient import TestClient

from rpi_node.camera_node import parse_source
from rpi_node.main import app


def test_rpi_source_parsing() -> None:
    assert parse_source("0") == 0
    assert parse_source("/dev/v4l/by-id/camera-face") == "/dev/v4l/by-id/camera-face"


def test_rpi_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["role"] == "camera-node"


def test_rpi_unknown_stream_is_404() -> None:
    with TestClient(app) as client:
        response = client.get("/stream/unknown")
    assert response.status_code == 404
