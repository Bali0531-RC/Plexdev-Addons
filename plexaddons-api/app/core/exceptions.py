from fastapi import HTTPException, status


class PlexAddonsException(HTTPException):
    """Base exception for PlexAddons API."""
    pass


class NotFoundError(PlexAddonsException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedError(PlexAddonsException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(PlexAddonsException):
    def __init__(self, detail: str = "Not authorized to perform this action"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestError(PlexAddonsException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ConflictError(PlexAddonsException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class StorageQuotaExceededError(PlexAddonsException):
    def __init__(self, detail: str = "Storage quota exceeded. Delete old versions or upgrade your plan."):
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class VersionLimitExceededError(PlexAddonsException):
    def __init__(self, detail: str = "Version history limit exceeded. Delete old versions or upgrade your plan."):
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class PaymentError(PlexAddonsException):
    def __init__(self, detail: str = "Payment processing error"):
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)
