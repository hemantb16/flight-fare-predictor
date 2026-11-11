"""Which airlines can fly a route, and how (non-stop or via their hubs).

Rules, deliberately simple but grounded in how airlines operate:

* Full-service carriers fly non-stop from their hubs. Short flights (≤ 2,500 km)
  may go to any airport. Medium-haul flights need a large airport (size ≥ 2) at
  the other end, and flights over 6,000 km need a major hub (size 3). Other
  routes connect through one of the carrier's hubs when the detour is
  reasonable. Carriers with several hubs offer two-stop itineraries only where
  they have nothing more direct.
* Low-cost carriers fly point-to-point. At least one end must be one of their
  bases, the other end must be in their network, and they sell no connections.
* Leisure carriers fly from their home bases to holiday destinations, but not
  between two of their own bases.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations

from .catalog import AIRLINES, AIRPORTS, FIRST_CLASS_KM, LONG_HAUL_KM, Airline, distance_km


@dataclass(frozen=True)
class Option:
    airline: str
    stops: int
    via: tuple[str, ...]
    flown_km: float

    @property
    def minutes(self) -> int:
        """Approximate door-to-door block time incl. taxiing and layovers."""
        legs = self.stops + 1
        return int(self.flown_km / 820 * 60 + 30 * legs + 105 * self.stops)

    @property
    def duration(self) -> str:
        h, m = divmod(round(self.minutes / 5) * 5, 60)
        return f"{h}h {m:02d}m"


def flies_nonstop(airline: Airline, origin: str, destination: str) -> bool:
    if origin == destination:
        return False
    dist = distance_km(origin, destination)
    if dist > airline.max_range:
        return False
    if airline.kind == "full-service":
        if origin not in airline.bases and destination not in airline.bases:
            return False
        other = destination if origin in airline.bases else origin
        if other in airline.bases:
            return True
        size = AIRPORTS[other].size
        if dist > 6000:
            return size >= 3 or (size >= 2 and AIRPORTS[other].season != "city")
        if dist > 2500:
            return size >= 2
        return True
    served = set(airline.bases) | set(airline.network)
    if origin not in served or destination not in served:
        return False
    in_base = (origin in airline.bases, destination in airline.bases)
    if not any(in_base):
        return False
    if all(in_base) and not airline.base_to_base:
        return False
    return True


def _detour_limit(dist: float) -> float:
    if dist < 1500:
        return 1.8
    if dist < 4000:
        return 1.5
    return 1.25


def airline_options(airline: Airline, origin: str, destination: str) -> list[Option]:
    dist = distance_km(origin, destination)
    options: list[Option] = []
    if flies_nonstop(airline, origin, destination):
        options.append(Option(airline.code, 0, (), dist))
    if airline.kind != "full-service":
        return options

    limit = _detour_limit(dist) * dist
    one_stop = [
        (distance_km(origin, h) + distance_km(h, destination), (h,))
        for h in airline.bases
        if h not in (origin, destination)
        and flies_nonstop(airline, origin, h)
        and flies_nonstop(airline, h, destination)
    ]
    one_stop = [c for c in one_stop if c[0] <= limit]
    if one_stop:
        flown, via = min(one_stop)
        options.append(Option(airline.code, 1, via, flown))

    # Two-stop itineraries are only sold when the carrier has nothing more direct.
    if not options and dist > 3000 and len(airline.bases) > 1:
        two_stop = [
            (distance_km(origin, h1) + distance_km(h1, h2) + distance_km(h2, destination), (h1, h2))
            for h1, h2 in permutations(airline.bases, 2)
            if origin not in (h1, h2) and destination not in (h1, h2)
            and flies_nonstop(airline, origin, h1)
            and flies_nonstop(airline, h2, destination)
        ]
        two_stop = [c for c in two_stop if c[0] <= limit * 1.1]
        if two_stop:
            flown, via = min(two_stop)
            options.append(Option(airline.code, 2, via, flown))
    return options


@lru_cache(maxsize=None)
def route_options(origin: str, destination: str) -> tuple[Option, ...]:
    """Every (airline, stops) way to fly a route, non-stop first."""
    if origin == destination or origin not in AIRPORTS or destination not in AIRPORTS:
        return ()
    options = [o for a in AIRLINES.values() for o in airline_options(a, origin, destination)]
    return tuple(sorted(options, key=lambda o: (o.stops, o.flown_km, AIRLINES[o.airline].name)))


def carriers_on_route(origin: str, destination: str) -> int:
    return len({o.airline for o in route_options(origin, destination)})


def cabins_for(airline: Airline, distance: float) -> tuple[str, ...]:
    cabins = ["economy"]
    if airline.premium and distance >= LONG_HAUL_KM:
        cabins.append("premium")
    if airline.business and (airline.kind == "full-service" or distance >= LONG_HAUL_KM or airline.code == "FZ"):
        cabins.append("business")
    if airline.first and distance >= FIRST_CLASS_KM:
        cabins.append("first")
    return tuple(cabins)


def find_option(origin: str, destination: str, airline: str, stops: int) -> Option | None:
    for o in route_options(origin, destination):
        if o.airline == airline and o.stops == stops:
            return o
    return None
