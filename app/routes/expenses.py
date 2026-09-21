import os

from flask import Blueprint, jsonify, request, send_from_directory
from pydantic import ValidationError
from sqlalchemy import func, select

from app.database import get_db
from app.http import (
    invalid_date_range_response,
    invalid_json_response,
    validation_error_response,
)
from app.models import Expense
from app.schemas import (
    ExpenseCreate,
    ExpenseListQuery,
    ExpenseListResponse,
    ExpenseResponse,
)
from app.services.auth import require_api_key
from app.spa import client_wants_html

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@expenses_bp.route("", methods=["POST"])
def create_expense():
    auth_error = require_api_key()
    if auth_error is not None:
        return auth_error
    body = request.get_json(silent=True)
    if body is None:
        return invalid_json_response()

    try:
        payload = ExpenseCreate.model_validate(body)
    except ValidationError as error:
        return validation_error_response(error)

    db = get_db()
    expense = Expense(
        amount=payload.amount,
        category=payload.category.value,
        payment_method=payload.payment_method.value,
        note=payload.note,
        date=payload.date,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    response = ExpenseResponse.model_validate(expense)
    return jsonify(response.model_dump(mode="json")), 201


@expenses_bp.route("", methods=["GET"])
def list_expenses():
    if client_wants_html(request):
        return send_from_directory(_STATIC_DIR, "index.html")

    auth_error = require_api_key()
    if auth_error is not None:
        return auth_error

    try:
        query_params = ExpenseListQuery.model_validate(request.args.to_dict())
    except ValidationError as error:
        return validation_error_response(error)

    if (
        query_params.start_date is not None
        and query_params.end_date is not None
        and query_params.start_date > query_params.end_date
    ):
        return invalid_date_range_response()

    filters = []
    if query_params.category is not None:
        filters.append(Expense.category == query_params.category.value)
    if query_params.payment_method is not None:
        filters.append(Expense.payment_method == query_params.payment_method.value)
    if query_params.start_date is not None:
        filters.append(Expense.date >= query_params.start_date)
    if query_params.end_date is not None:
        filters.append(Expense.date <= query_params.end_date)

    base_query = select(Expense)
    if filters:
        base_query = base_query.where(*filters)

    db = get_db()
    count_query = select(func.count()).select_from(Expense)
    if filters:
        count_query = count_query.where(*filters)
    total = db.scalar(count_query) or 0

    items_query = (
        base_query.order_by(Expense.date.desc(), Expense.id.desc())
        .offset(query_params.offset)
        .limit(query_params.limit)
    )
    items = list(db.scalars(items_query).all())

    response = ExpenseListResponse(
        items=[ExpenseResponse.model_validate(item) for item in items],
        total=total,
        limit=query_params.limit,
        offset=query_params.offset,
    )
    return jsonify(response.model_dump(mode="json"))
