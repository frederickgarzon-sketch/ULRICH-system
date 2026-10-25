"""Launch the Raspberry Pi dual-camera streaming node."""

import uvicorn

from rpi_node.config import settings

if __name__ == "__main__":
    print(f"Camera node: http://0.0.0.0:{settings.port}")
    print(f"Face stream: http://<PI-IP>:{settings.port}/stream/face")
    print(f"Body stream: http://<PI-IP>:{settings.port}/stream/body")
    print(f"Mode: {'MOCK' if settings.mock_mode else 'USB'}")
    uvicorn.run("rpi_node.main:app", host=settings.host, port=settings.port, workers=1)

