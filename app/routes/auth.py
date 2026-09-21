from flask import Blueprint, g, jsonify, request
from pydantic import BaseModel, ValidationError

from app.database import get_db
from app.http import (
    auth_not_configured_response,
    invalid_admin_password_response,
    invalid_json_response,
    validation_error_response,
)
from app.services.auth import (
    api_key_metadata,
    require_api_key_for_auth_routes,
    rotate_api_key,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class RotateRequest(BaseModel):
    password: str


@auth_bp.before_request
def _require_api_key():
    result = require_api_key_for_auth_routes()
    if result is not None:
        return result


@auth_bp.route("/verify", methods=["GET"])
def verify():
    record = g.api_key
    return jsonify(
        {
            "authenticated": True,
            "key": api_key_metadata(record),
        }
    )


@auth_bp.route("/api-key", methods=["GET"])
def api_key_info():
    return jsonify(api_key_metadata(g.api_key))


@auth_bp.route("/api-key/rotate", methods=["POST"])
def api_key_rotate():
    body = request.get_json(silent=True)
    if body is None:
        return invalid_json_response()
    try:
        payload = RotateRequest.model_validate(body)
    except ValidationError as error:
        return validation_error_response(error)
    try:
        raw_new, new_record, grace_until = rotate_api_key(
            get_db(), g.api_key, payload.password
        )
    except PermissionError:
        return invalid_admin_password_response()
    except RuntimeError:
        return auth_not_configured_response()
    return jsonify(
        {
            "api_key": raw_new,
            "key": {
                "prefix": api_key_metadata(new_record)["prefix"],
                "created_at": new_record.created_at.isoformat(),
            },
            "previous_key_valid_until": grace_until.isoformat(),
        }
    )
