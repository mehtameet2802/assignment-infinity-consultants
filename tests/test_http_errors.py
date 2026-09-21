from pydantic import BaseModel, Field, ValidationError

from app.http import error_response, validation_error_response


class _SampleModel(BaseModel):
    amount: int = Field(gt=0)


def test_error_response_shape(app):
    with app.app_context():
        response, status_code = error_response(
            "validation_error",
            [{"field": "amount", "message": "Input should be greater than 0"}],
            422,
        )
    assert status_code == 422
    assert response.get_json() == {
        "error": "validation_error",
        "details": [
            {"field": "amount", "message": "Input should be greater than 0"},
        ],
    }


def test_validation_error_response_maps_pydantic_errors(app):
    try:
        _SampleModel.model_validate({"amount": 0})
    except ValidationError as error:
        with app.app_context():
            response, status_code = validation_error_response(error)
    else:
        raise AssertionError("expected validation error")

    assert status_code == 422
    body = response.get_json()
    assert body["error"] == "validation_error"
    assert body["details"] == [
        {"field": "amount", "message": "Input should be greater than 0"},
    ]
