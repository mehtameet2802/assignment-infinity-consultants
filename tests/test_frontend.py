def test_index_returns_frontend_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Spend Tracker" in response.data
    assert b'id="view-dashboard"' in response.data


def test_static_js_asset_reachable(client):
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert b"initApp" in response.data


def test_static_css_asset_reachable(client):
    response = client.get("/static/css/app.css")
    assert response.status_code == 200


def test_expenses_path_returns_frontend_html(client):
    response = client.get("/expenses", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert b'id="view-expenses"' in response.data


def test_analytics_path_returns_frontend_html(client):
    response = client.get("/analytics")
    assert response.status_code == 200
    assert b'id="view-analytics"' in response.data


def test_expenses_api_still_json_without_html_accept(client):
    response = client.get("/expenses")
    assert response.status_code == 200
    assert response.is_json
    assert "items" in response.get_json()
