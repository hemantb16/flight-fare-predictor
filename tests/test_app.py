import re


def test_homepage_renders_form(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert '<form class="card search-card" action="/result"' in html
    for name in ["origin", "destination", "travel_date", "airline", "cabin", "stops", "time_slot"]:
        assert f'name="{name}"' in html


def test_homepage_has_no_third_party_requests(client):
    html = client.get("/").get_data(as_text=True)
    assert not re.search(r'(src|href)="https?://', html)


def test_result_page_shows_estimate(client, valid_trip):
    res = client.get("/result", query_string=valid_trip)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    match = re.search(r'data-testid="fare">€([\d,.]+)<', html)
    assert match, "fare not rendered"
    fare = float(match.group(1).replace(",", ""))
    assert 40 < fare < 600  # Berlin -> London economy, one month ahead
    assert "Airlines on this route" in html
    assert "2 passengers" in html


def test_result_page_with_invalid_input_shows_errors(client, valid_trip):
    res = client.get("/result", query_string={**valid_trip, "destination": "BER"})
    assert res.status_code == 400
    html = res.get_data(as_text=True)
    assert "Arrival city must differ" in html
    assert 'aria-invalid="true"' in html


def test_api_predict_returns_sensible_price(client, valid_trip):
    res = client.post("/api/predict", json=valid_trip)
    assert res.status_code == 200
    body = res.get_json()
    assert body["currency"] == "EUR"
    assert 40 < body["fare_per_passenger"] < 600
    assert body["range"]["low"] < body["fare_per_passenger"] < body["range"]["high"]
    assert body["total"] == round(body["fare_per_passenger"] * 2, 2)
    assert body["trip"]["days_before"] == 30


def test_api_long_haul_business_costs_more(client, valid_trip):
    economy = client.post("/api/predict", json={**valid_trip, "destination": "SIN"}).get_json()
    business = client.post(
        "/api/predict", json={**valid_trip, "destination": "SIN", "cabin": "business"}
    ).get_json()
    assert business["fare_per_passenger"] > economy["fare_per_passenger"] * 2
    assert economy["fare_per_passenger"] > 300


def test_api_rejects_invalid_input(client, valid_trip):
    res = client.post("/api/predict", json={**valid_trip, "airline": "NOPE", "passengers": "42"})
    assert res.status_code == 400
    errors = res.get_json()["errors"]
    assert set(errors) == {"airline", "passengers"}


def test_api_rejects_non_json(client):
    res = client.post("/api/predict", data="hello", content_type="text/plain")
    assert res.status_code == 400


def test_health_and_404(client):
    assert client.get("/health").get_json()["status"] == "ok"
    assert client.get("/nowhere").status_code == 404
