"""Custom business exceptions and global HTTP error handlers."""

from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Base class for all business domain exceptions."""

    status_code = 500
    code = "internal_error"

    def __init__(self, code: str | None = None, message: str = "", status: int | None = None):
        super().__init__(message)
        if code:
            self.code = code
        if status:
            self.status_code = status
        self.message = message


class BadRequest(ApiError):
    """Raised when client input cannot be parsed (400)."""

    status_code = 400
    code = "bad_request"


class NotFound(ApiError):
    """Raised when a requested resource does not exist or is soft-deleted (404)."""

    status_code = 404
    code = "not_found"


class Conflict(ApiError):
    """Raised on state conflicts such as duplicate SKU (409)."""

    status_code = 409
    code = "conflict"


class OutOfStock(ApiError):
    """Raised when reserving or ordering more units than available in stock (409)."""

    status_code = 409
    code = "out_of_stock"


def register_error_handlers(app) -> None:
    """Register global error handlers for domain, validation, and HTTP exceptions."""

    @app.errorhandler(ApiError)
    def _on_api_error(err: ApiError):
        return (
            jsonify(
                {
                    "code": err.code,
                    "error": err.code,
                    "message": err.message,
                    "detail": err.message,
                }
            ),
            err.status_code,
        )

    @app.errorhandler(ValidationError)
    def _on_validation_error(err: ValidationError):
        return (
            jsonify(
                {
                    "code": "validation_error",
                    "error": "validation_error",
                    "message": "Input validation failed",
                    "detail": err.messages,
                }
            ),
            422,
        )

    @app.errorhandler(HTTPException)
    def _on_http_error(err: HTTPException):
        code_slug = err.name.lower().replace(" ", "_")
        return (
            jsonify(
                {
                    "code": code_slug,
                    "error": code_slug,
                    "message": err.description,
                    "detail": err.description,
                }
            ),
            err.code,
        )

    @app.errorhandler(Exception)
    def _on_unexpected_error(err: Exception):
        app.logger.exception("unhandled")
        return (
            jsonify(
                {
                    "code": "internal_error",
                    "error": "internal_error",
                    "message": "An unexpected internal error occurred",
                    "detail": "An unexpected internal error occurred",
                }
            ),
            500,
        )
