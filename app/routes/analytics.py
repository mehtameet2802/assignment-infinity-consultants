from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.analytics_schemas import SummaryQuery
from app.database import get_db
from app.http import error_response, invalid_month_range_response, validation_error_response
from app.services.analytics import get_summary

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/summary", methods=["GET"])
def summary():
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")

    missing_fields = []
    if start_month is None or start_month == "":
        missing_fields.append(
            {"field": "start_month", "message": "start_month is required"}
        )
    if end_month is None or end_month == "":
        missing_fields.append(
            {"field": "end_month", "message": "end_month is required"}
        )
    if missing_fields:
        return error_response("validation_error", missing_fields, 422)

    try:
        query = SummaryQuery.model_validate(
            {"start_month": start_month, "end_month": end_month}
        )
    except ValidationError as error:
        return validation_error_response(error)

    if query.start_month > query.end_month:
        return invalid_month_range_response()

    db = get_db()
    data = get_summary(db, query.start_month, query.end_month)
    return jsonify(data.model_dump(mode="json"))
