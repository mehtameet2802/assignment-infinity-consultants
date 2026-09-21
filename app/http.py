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
