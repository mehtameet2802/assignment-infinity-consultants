def test_unknown_api_route_returns_json_not_found(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.get_json()
    assert body["error"] == "not_found"
    assert body["details"][0]["message"]


def test_wrong_method_returns_json(client):
    response = client.post("/health")
    assert response.status_code == 405
    body = response.get_json()
    assert body["error"] == "method_not_allowed"
