from itertools import permutations

from flightfare.catalog import AIRLINES, AIRPORTS, distance_km
from flightfare.network import cabins_for, carriers_on_route, route_options


def airlines_on(o, d, stops=None):
    return {x.airline for x in route_options(o, d) if stops is None or x.stops == stops}


def test_distance_is_plausible():
    assert 6000 < distance_km("FRA", "JFK") < 6400
    assert 450 < distance_km("BER", "MUC") < 550


def test_catalog_size():
    assert len(AIRPORTS) >= 90
    assert len(AIRLINES) >= 50


def test_hub_carriers_fly_nonstop_from_their_hubs():
    assert {"LH", "DL"} <= airlines_on("FRA", "JFK", stops=0)
    assert "BA" in airlines_on("BER", "LHR", stops=0)


def test_hub_carriers_connect_through_hubs():
    options = {(x.airline, x.via) for x in route_options("HAM", "BKK") if x.stops == 1}
    assert ("EK", ("DXB",)) in options
    assert ("TK", ("IST",)) in options


def test_low_cost_carriers_stay_in_their_network():
    assert "FR" in airlines_on("CGN", "PMI", stops=0)
    assert "FR" not in airlines_on("FRA", "JFK")
    assert all(x.stops == 0 for x in route_options("BER", "LGW") if x.airline == "U2")


def test_leisure_carriers_do_not_fly_between_their_bases():
    assert "DE" in airlines_on("FRA", "PMI", stops=0)
    assert "DE" not in airlines_on("FRA", "MUC")


def test_unrealistic_detours_are_excluded():
    assert not any(x.via and x.via[0] in ("SFO", "LAX", "YVR") for x in route_options("MUC", "SYD") if x.stops == 1)


def test_almost_every_route_is_served():
    pairs = list(permutations(AIRPORTS, 2))
    missing = [p for p in pairs if not route_options(*p)]
    assert len(missing) / len(pairs) < 0.01


def test_cabins_depend_on_airline_and_distance():
    assert cabins_for(AIRLINES["FR"], 1500) == ("economy",)
    assert "first" not in cabins_for(AIRLINES["LH"], 600)
    assert "first" in cabins_for(AIRLINES["LH"], 9000)
    assert "premium" in cabins_for(AIRLINES["LH"], 9000)


def test_busy_routes_have_more_carriers():
    assert carriers_on_route("FRA", "JFK") > carriers_on_route("BRE", "LIS")
