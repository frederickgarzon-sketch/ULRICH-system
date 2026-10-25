import pytest
from pydantic import ValidationError
from app.api import routes


def test_legacy_verification_bypass_is_rejected():
    with pytest.raises(ValidationError):
        routes.SessionStart(participant_id=1, verification_override=True)


def test_framing_override_endpoint_is_removed():
    assert not any(route.path.endswith('/missing-joints-override') for route in routes.router.routes)
