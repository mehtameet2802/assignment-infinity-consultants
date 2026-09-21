from flask import jsonify
from pydantic import ValidationError


def error_response(error_code: str, details: list[dict], status_code: int):
    return jsonify({"error": error_code, "details": details}), status_code


def validation_error_response(error: ValidationError):
    details = []
    for item in error.errors(include_url=False, include_context=False):
        location = item.get("loc", ())
        field = str(location[-1]) if location else None
        details.append({"field": field, "message": item["msg"]})
    return error_response("validation_error", details, 422)


def invalid_json_response():
    return error_response(
        "invalid_json",
        [{"field": None, "message": "Request body must be valid JSON"}],
        400,
    )


def invalid_date_range_response():
    return error_response(
        "invalid_date_range",
        [
            {
                "field": "start_date",
                "message": "start_date must not be after end_date",
            }
        ],
        400,
    )


def unauthorized_response():
    return error_response(
        "unauthorized",
        [{"field": None, "message": "A valid API key is required"}],
        401,
    )


def auth_not_configured_response():
    return error_response(
        "auth_not_configured",
        [{"field": None, "message": "API authentication is not configured"}],
        503,
    )


def invalid_admin_password_response():
    return error_response(
        "invalid_admin_password",
        [
            {
                "field": "password",
                "message": "Administrator password is incorrect",
            }
        ],
        403,
    )


def invalid_month_range_response():
    return error_response(
        "invalid_month_range",
        [
            {
                "field": "start_month",
                "message": "start_month must not be after end_month",
            }
        ],
        400,
    )
