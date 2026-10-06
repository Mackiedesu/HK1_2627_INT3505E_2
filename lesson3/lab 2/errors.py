import logging
import uuid
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

ERROR_BASE = "https://api.example.com/probs"

logger = logging.getLogger(__name__)


class ApiProblem(Exception):
    def __init__(
        self,
        status: int = 400,
        title: str = "Bad Request",
        detail: str = None,
        type_path: str = None,
        type: str = None,
        **extra
    ):
        super().__init__(title)
        self.status = status
        self.title = title
        self.detail = detail
        self.type_path = type_path
        if type:
            self.type = type
        elif type_path:
            self.type = f"{ERROR_BASE}/{type_path}"
        else:
            self.type = "about:blank"
        self.extra = extra


ProblemError = ApiProblem


def _problem(
    status: int,
    title: str,
    detail: str = None,
    type_path: str = None,
    type: str = None,
    trace_id: str = None,
    **extra
):
    if type:
        problem_type = type
    elif type_path:
        problem_type = f"{ERROR_BASE}/{type_path}"
    else:
        problem_type = "about:blank"

    body = {
        "type": problem_type,
        "title": title,
        "status": status,
        "instance": request.path if request else "about:blank",
        "trace_id": trace_id or str(uuid.uuid4()),
    }

    if detail:
        body["detail"] = detail

    body.update(extra)

    resp = jsonify(body)
    resp.status_code = status
    resp.headers["Content-Type"] = "application/problem+json"
    return resp


problem_response = _problem


def register_error_handlers(app):
    @app.errorhandler(ApiProblem)
    def handle_api_problem(error: ApiProblem):
        return _problem(
            status=error.status,
            title=error.title,
            detail=error.detail,
            type=error.type,
            **error.extra
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        slug = error.name.lower().replace(" ", "-")
        return _problem(
            status=error.code or 500,
            title=error.name,
            detail=error.description,
            type_path=slug
        )

    @app.errorhandler(Exception)
    def handle_unhandled_exception(error: Exception):
        trace_id = str(uuid.uuid4())
        app.logger.error(
            f"Unhandled server error occurred [trace_id={trace_id}]: {error}",
            exc_info=True
        )
        return _problem(
            status=500,
            title="Internal Server Error",
            detail="An unexpected error occurred. Please contact support with the trace_id.",
            type_path="internal-server-error",
            trace_id=trace_id
        )
