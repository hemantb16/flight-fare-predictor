import re


def fare_from(html: str) -> float:
    match = re.search(r'data-testid="fare">€([\d,]+)<', html)
    assert match, "fare not rendered"
    return float(match.group(1).replace(",", ""))


def test_homepage_renders_form(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'action="/result"' in html
    for name in ["origin", "destination", "travel_date", "cabin", "airline", "stops", "time_slot", "passengers"]:
        assert f'name="{name}"' in html
    assert 'name="booking_date"' not in html
    assert html.count("<option value=") > 150  # airports in the datalist + menus


def test_pages_make_no_third_party_requests(client, valid_search):
    for html in (client.get("/").get_data(as_text=True), client.get("/result", query_string=valid_search).get_data(as_text=True)):
        assert not re.search(r'(src|href)="(https?:)?//', html)


def test_result_page_shows_estimate_and_flights(client, valid_search):
    res = client.get("/result", query_string=valid_search)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 40 < fare_from(html) < 400  # Berlin -> London economy, one month ahead
    assert "British Airways" in html
    assert "Nearby dates" in html and "When to book" in html
    assert "2 passengers" in html


def test_airline_filter_limits_results(client, valid_search):
    html = client.get("/result", query_string={**valid_search, "airline": "BA", "stops": "0"}).get_data(as_text=True)
    assert "British Airways" in html
    assert "KLM" not in html


def test_result_page_with_invalid_input_shows_errors(client, valid_search):
    res = client.get("/result", query_string={**valid_search, "destination": "Berlin (BER)"})
    assert res.status_code == 400
    html = res.get_data(as_text=True)
    assert "Arrival must differ" in html
    assert 'aria-invalid="true"' in html


def test_api_route_lists_airlines(client):
    body = client.get("/api/route", query_string={"origin": "FRA", "destination": "JFK"}).get_json()
    codes = {a["code"] for a in body["airlines"]}
    assert {"LH", "DL", "BA"} <= codes
    assert body["nonstop"] is True
    assert "first" in body["cabins"]


def test_api_predict_returns_sensible_price(client, valid_search):
    res = client.post("/api/predict", json=valid_search)
    assert res.status_code == 200
    body = res.get_json()
    assert body["currency"] == "EUR"
    cheapest = body["cheapest"]
    assert 40 < cheapest["fare"] < 400
    assert cheapest["range"]["low"] < cheapest["fare"] < cheapest["range"]["high"]
    assert body["total"] == round(cheapest["fare"] * 2, 2)
    assert body["days_before"] == 30
    fares = [i["fare"] for i in body["itineraries"]]
    assert fares == sorted(fares)


def test_api_long_haul_business_costs_more(client, valid_search):
    trip = {**valid_search, "origin": "FRA", "destination": "SIN"}
    economy = client.post("/api/predict", json=trip).get_json()["cheapest"]["fare"]
    business = client.post("/api/predict", json={**trip, "cabin": "business"}).get_json()["cheapest"]["fare"]
    assert economy > 350
    assert business > economy * 2.5


def test_api_rejects_invalid_input(client, valid_search):
    res = client.post("/api/predict", json={**valid_search, "airline": "NOPE", "passengers": "42"})
    assert res.status_code == 400
    assert set(res.get_json()["errors"]) == {"airline", "passengers"}


def test_api_rejects_non_json(client):
    assert client.post("/api/predict", data="hello", content_type="text/plain").status_code == 400


def test_health_and_404(client):
    assert client.get("/health").get_json()["status"] == "ok"
    assert client.get("/nowhere").status_code == 404
