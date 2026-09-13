import pytest
from pydantic import ValidationError

from app.schemas.foundation import (
    EventFoundationInput,
    RegistrationFoundationInput,
)


@pytest.mark.parametrize("capacity", [0, -1])
def test_event_capacity_must_be_positive(capacity: int) -> None:
    with pytest.raises(ValidationError):
        EventFoundationInput(capacity=capacity, status="draft")


def test_invalid_event_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EventFoundationInput(capacity=1, status="archived")


def test_invalid_registration_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RegistrationFoundationInput(status="pending")
