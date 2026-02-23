"""Tests for custom exception classes."""
from fastapi import status
from app.core.exceptions import (
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    ConflictError,
    StorageQuotaExceededError,
    VersionLimitExceededError,
    PaymentError,
)


class TestExceptions:
    def test_not_found_default(self):
        exc = NotFoundError()
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.detail == "Resource not found"

    def test_not_found_custom(self):
        exc = NotFoundError("Addon not found")
        assert exc.detail == "Addon not found"

    def test_unauthorized_default(self):
        exc = UnauthorizedError()
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "Not authenticated"

    def test_unauthorized_has_header(self):
        exc = UnauthorizedError()
        assert exc.headers == {"WWW-Authenticate": "Bearer"}

    def test_forbidden(self):
        exc = ForbiddenError()
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_bad_request(self):
        exc = BadRequestError("Invalid input")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.detail == "Invalid input"

    def test_conflict(self):
        exc = ConflictError()
        assert exc.status_code == status.HTTP_409_CONFLICT

    def test_storage_quota(self):
        exc = StorageQuotaExceededError()
        assert exc.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Storage quota" in exc.detail

    def test_version_limit(self):
        exc = VersionLimitExceededError()
        assert exc.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "Version history limit" in exc.detail

    def test_payment_error(self):
        exc = PaymentError("Card declined")
        assert exc.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert exc.detail == "Card declined"
