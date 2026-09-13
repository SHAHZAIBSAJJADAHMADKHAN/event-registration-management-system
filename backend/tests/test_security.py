import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jwt import PyJWK

from app.core.security import JWTVerificationError, JWTVerifier, get_jwt_verifier
from app.database.profiles import ProfileRepository
from app.dependencies.auth import (
    get_profile_repository,
    require_admin,
    require_attendee_owned_resource,
)
from app.main import app
from app.schemas.auth import AuthenticatedUser, UserRole


ISSUER = "https://auth.example.test"
USER_ID = uuid4()


class StubJWKClient:
    def __init__(self, key: PyJWK) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, _: str) -> PyJWK:
        return self.key


class StubVerifier:
    def __init__(self, claims: dict[str, object] | None = None) -> None:
        self.claims = claims or {"sub": str(USER_ID)}

    def verify(self, token: str) -> dict[str, object]:
        if token != "valid-token":
            raise JWTVerificationError("invalid")
        return self.claims


class StubProfiles:
    def __init__(self, user: AuthenticatedUser | None) -> None:
        self.user = user

    def get_authenticated_user(self, _):
        return self.user


@pytest.fixture
def signing_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    verifier = JWTVerifier(ISSUER, "https://jwks.example.test")
    verifier._jwks_client = StubJWKClient(PyJWK.from_dict(public_jwk))
    return private_key, verifier


def make_token(private_key, **overrides: object) -> str:
    claims = {
        "sub": str(USER_ID),
        "iss": ISSUER,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def test_jwt_verifier_accepts_valid_token(signing_material) -> None:
    private_key, verifier = signing_material

    assert verifier.verify(make_token(private_key))["sub"] == str(USER_ID)


def test_jwt_verifier_rejects_malformed_invalid_signature_expired_and_wrong_issuer(signing_material) -> None:
    private_key, verifier = signing_material
    other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    for token in (
        "not-a-jwt",
        make_token(other_private_key),
        make_token(private_key, exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
        make_token(private_key, iss="https://wrong-issuer.example.test"),
    ):
        with pytest.raises(JWTVerificationError):
            verifier.verify(token)


@pytest.fixture
def api_client():
    user = AuthenticatedUser(id=USER_ID, full_name="Test attendee", role=UserRole.ATTENDEE)
    app.dependency_overrides[get_jwt_verifier] = lambda: StubVerifier()
    app.dependency_overrides[get_profile_repository] = lambda: StubProfiles(user)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_no_token_is_rejected(api_client: TestClient) -> None:
    response = api_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"


def test_malformed_token_is_rejected(api_client: TestClient) -> None:
    response = api_client.get("/api/auth/me", headers={"Authorization": "Bearer malformed"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


def test_valid_attendee_is_resolved_from_profile_not_token_role(api_client: TestClient) -> None:
    response = api_client.get("/api/auth/me", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.json()["id"] == str(USER_ID)
    assert response.json()["role"] == "attendee"


def test_role_guards_and_attendee_ownership_are_enforced() -> None:
    attendee = AuthenticatedUser(id=USER_ID, full_name="Attendee", role=UserRole.ATTENDEE)
    admin = AuthenticatedUser(id=uuid4(), full_name="Admin", role=UserRole.ADMIN)

    with pytest.raises(HTTPException) as attendee_as_admin:
        asyncio.run(require_admin(attendee))
    assert attendee_as_admin.value.status_code == 403

    assert asyncio.run(require_admin(admin)) == admin
    assert asyncio.run(require_attendee_owned_resource(USER_ID, attendee)) == attendee

    with pytest.raises(HTTPException) as another_attendee_resource:
        asyncio.run(require_attendee_owned_resource(uuid4(), attendee))
    assert another_attendee_resource.value.status_code == 403
    assert another_attendee_resource.value.detail["code"] == "ownership_required"
