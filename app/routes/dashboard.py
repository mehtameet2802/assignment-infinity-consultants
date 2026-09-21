from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.dashboard_schemas import DashboardQuery
from app.database import get_db
from app.http import error_response, validation_error_response
from app.services.dashboard import get_dashboard

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    month = request.args.get("month")
    if month is None or month == "":
        return error_response(
            "validation_error",
            [{"field": "month", "message": "month is required"}],
            422,
        )

    try:
        query = DashboardQuery.model_validate({"month": month})
    except ValidationError as error:
        return validation_error_response(error)

    db = get_db()
    data = get_dashboard(db, query.month)
    return jsonify(data.model_dump(mode="json"))
