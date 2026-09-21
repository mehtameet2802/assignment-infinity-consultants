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
