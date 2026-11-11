"""Reference data: airports, airlines, cabins and departure time slots.

Airports use their real IATA codes and approximate coordinates (only needed for
great-circle distances). Airlines are real carriers. Their networks are simplified
models of how each one operates (hub carrier, low-cost or leisure). They are not
live schedules, so a listed route is plausible rather than guaranteed to exist.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Airport:
    code: str
    city: str
    country: str
    lat: float
    lon: float
    size: int  # 3 = major intercontinental hub, 2 = large airport, 1 = regional
    season: str  # "city", "summer" (beach peak Jun-Sep) or "winter" (winter-sun peak Nov-Mar)
    demand: float  # relative popularity (1.0 = average)

    @property
    def label(self) -> str:
        return f"{self.city} ({self.code})"


def _ap(code, city, country, lat, lon, size=2, season="city", demand=1.0):
    return Airport(code, city, country, lat, lon, size, season, demand)


AIRPORTS: dict[str, Airport] = {
    a.code: a
    for a in [
        # Germany
        _ap("BER", "Berlin", "Germany", 52.366, 13.503, 2, demand=1.02),
        _ap("FRA", "Frankfurt", "Germany", 50.038, 8.562, 3, demand=1.03),
        _ap("MUC", "Munich", "Germany", 48.354, 11.786, 3, demand=1.04),
        _ap("HAM", "Hamburg", "Germany", 53.630, 9.988, 2, demand=0.98),
        _ap("DUS", "Düsseldorf", "Germany", 51.289, 6.767, 2, demand=0.98),
        _ap("CGN", "Cologne/Bonn", "Germany", 50.866, 7.143, 1, demand=0.95),
        _ap("STR", "Stuttgart", "Germany", 48.690, 9.222, 1, demand=0.97),
        _ap("HAJ", "Hanover", "Germany", 52.461, 9.685, 1, demand=0.94),
        _ap("NUE", "Nuremberg", "Germany", 49.499, 11.078, 1, demand=0.94),
        _ap("LEJ", "Leipzig/Halle", "Germany", 51.424, 12.236, 1, demand=0.92),
        _ap("DRS", "Dresden", "Germany", 51.133, 13.767, 1, demand=0.92),
        _ap("BRE", "Bremen", "Germany", 53.048, 8.787, 1, demand=0.92),
        # Rest of Europe
        _ap("LHR", "London Heathrow", "United Kingdom", 51.470, -0.454, 3, demand=1.12),
        _ap("LGW", "London Gatwick", "United Kingdom", 51.153, -0.182, 2, demand=1.08),
        _ap("MAN", "Manchester", "United Kingdom", 53.354, -2.275, 2, demand=0.98),
        _ap("EDI", "Edinburgh", "United Kingdom", 55.950, -3.373, 2, demand=1.02),
        _ap("DUB", "Dublin", "Ireland", 53.421, -6.270, 3, demand=1.03),
        _ap("CDG", "Paris", "France", 49.010, 2.548, 3, demand=1.10),
        _ap("NCE", "Nice", "France", 43.658, 7.216, 2, "summer", 1.06),
        _ap("LYS", "Lyon", "France", 45.726, 5.081, 1, demand=0.96),
        _ap("AMS", "Amsterdam", "Netherlands", 52.310, 4.768, 3, demand=1.06),
        _ap("BRU", "Brussels", "Belgium", 50.901, 4.484, 2, demand=0.99),
        _ap("ZRH", "Zurich", "Switzerland", 47.458, 8.548, 3, demand=1.08),
        _ap("GVA", "Geneva", "Switzerland", 46.238, 6.109, 2, demand=1.05),
        _ap("VIE", "Vienna", "Austria", 48.110, 16.570, 3, demand=1.01),
        _ap("CPH", "Copenhagen", "Denmark", 55.618, 12.656, 3, demand=1.02),
        _ap("ARN", "Stockholm", "Sweden", 59.650, 17.919, 2, demand=1.00),
        _ap("OSL", "Oslo", "Norway", 60.194, 11.100, 2, demand=1.01),
        _ap("HEL", "Helsinki", "Finland", 60.317, 24.963, 3, demand=0.99),
        _ap("MAD", "Madrid", "Spain", 40.472, -3.561, 3, demand=1.03),
        _ap("BCN", "Barcelona", "Spain", 41.297, 2.078, 3, "summer", 1.09),
        _ap("PMI", "Palma de Mallorca", "Spain", 39.552, 2.736, 2, "summer", 1.08),
        _ap("AGP", "Málaga", "Spain", 36.675, -4.499, 2, "summer", 1.05),
        _ap("ALC", "Alicante", "Spain", 38.282, -0.558, 2, "summer", 1.00),
        _ap("TFS", "Tenerife South", "Spain", 28.044, -16.572, 2, "winter", 1.04),
        _ap("LPA", "Gran Canaria", "Spain", 27.932, -15.387, 2, "winter", 1.03),
        _ap("LIS", "Lisbon", "Portugal", 38.774, -9.134, 3, demand=1.05),
        _ap("OPO", "Porto", "Portugal", 41.248, -8.681, 2, demand=1.02),
        _ap("FAO", "Faro", "Portugal", 37.014, -7.966, 2, "summer", 1.03),
        _ap("FCO", "Rome", "Italy", 41.800, 12.239, 3, demand=1.07),
        _ap("MXP", "Milan", "Italy", 45.630, 8.723, 2, demand=1.02),
        _ap("VCE", "Venice", "Italy", 45.505, 12.352, 2, demand=1.06),
        _ap("NAP", "Naples", "Italy", 40.886, 14.291, 2, "summer", 1.03),
        _ap("CTA", "Catania", "Italy", 37.467, 15.066, 2, "summer", 1.01),
        _ap("ATH", "Athens", "Greece", 37.936, 23.947, 2, "summer", 1.04),
        _ap("HER", "Heraklion (Crete)", "Greece", 35.340, 25.180, 2, "summer", 1.05),
        _ap("LCA", "Larnaca", "Cyprus", 34.875, 33.625, 2, "summer", 1.00),
        _ap("PRG", "Prague", "Czechia", 50.101, 14.260, 2, demand=1.00),
        _ap("WAW", "Warsaw", "Poland", 52.166, 20.967, 2, demand=0.96),
        _ap("KRK", "Kraków", "Poland", 50.078, 19.785, 2, demand=0.97),
        _ap("BUD", "Budapest", "Hungary", 47.437, 19.256, 2, demand=0.97),
        _ap("OTP", "Bucharest", "Romania", 44.571, 26.085, 2, demand=0.93),
        _ap("SOF", "Sofia", "Bulgaria", 42.697, 23.411, 1, demand=0.92),
        _ap("IST", "Istanbul", "Türkiye", 41.275, 28.752, 3, demand=1.02),
        _ap("AYT", "Antalya", "Türkiye", 36.899, 30.801, 2, "summer", 1.02),
        # Middle East & Africa
        _ap("DXB", "Dubai", "United Arab Emirates", 25.253, 55.365, 3, "winter", 1.08),
        _ap("AUH", "Abu Dhabi", "United Arab Emirates", 24.433, 54.651, 3, "winter", 1.00),
        _ap("DOH", "Doha", "Qatar", 25.273, 51.608, 3, demand=0.98),
        _ap("TLV", "Tel Aviv", "Israel", 32.011, 34.887, 2, demand=1.02),
        _ap("CAI", "Cairo", "Egypt", 30.122, 31.406, 2, demand=0.95),
        _ap("HRG", "Hurghada", "Egypt", 27.178, 33.799, 2, "winter", 0.96),
        _ap("RAK", "Marrakesh", "Morocco", 31.607, -8.036, 2, "winter", 1.00),
        _ap("NBO", "Nairobi", "Kenya", -1.319, 36.928, 2, demand=0.97),
        _ap("JNB", "Johannesburg", "South Africa", -26.139, 28.246, 3, demand=0.98),
        _ap("CPT", "Cape Town", "South Africa", -33.970, 18.602, 2, "winter", 1.05),
        # Asia & Oceania
        _ap("DEL", "Delhi", "India", 28.556, 77.100, 3, demand=0.97),
        _ap("BOM", "Mumbai", "India", 19.089, 72.868, 3, demand=0.98),
        _ap("BLR", "Bengaluru", "India", 13.199, 77.706, 2, demand=0.97),
        _ap("MLE", "Malé (Maldives)", "Maldives", 4.192, 73.529, 2, "winter", 1.12),
        _ap("BKK", "Bangkok", "Thailand", 13.690, 100.750, 3, "winter", 1.04),
        _ap("SIN", "Singapore", "Singapore", 1.364, 103.991, 3, demand=1.06),
        _ap("KUL", "Kuala Lumpur", "Malaysia", 2.746, 101.710, 3, demand=0.97),
        _ap("DPS", "Bali (Denpasar)", "Indonesia", -8.748, 115.167, 2, "winter", 1.07),
        _ap("HKG", "Hong Kong", "Hong Kong", 22.308, 113.918, 3, demand=1.05),
        _ap("PEK", "Beijing", "China", 40.080, 116.585, 3, demand=0.98),
        _ap("PVG", "Shanghai", "China", 31.143, 121.805, 3, demand=1.00),
        _ap("ICN", "Seoul", "South Korea", 37.460, 126.441, 3, demand=1.03),
        _ap("HND", "Tokyo", "Japan", 35.549, 139.780, 3, demand=1.10),
        _ap("SYD", "Sydney", "Australia", -33.946, 151.177, 3, demand=1.07),
        _ap("MEL", "Melbourne", "Australia", -37.669, 144.841, 3, demand=1.03),
        # Americas
        _ap("JFK", "New York", "United States", 40.641, -73.778, 3, demand=1.12),
        _ap("BOS", "Boston", "United States", 42.366, -71.010, 3, demand=1.04),
        _ap("IAD", "Washington", "United States", 38.953, -77.456, 3, demand=1.01),
        _ap("ORD", "Chicago", "United States", 41.978, -87.905, 3, demand=1.02),
        _ap("ATL", "Atlanta", "United States", 33.637, -84.428, 3, demand=0.99),
        _ap("MIA", "Miami", "United States", 25.793, -80.291, 3, "winter", 1.06),
        _ap("LAX", "Los Angeles", "United States", 33.942, -118.408, 3, demand=1.08),
        _ap("SFO", "San Francisco", "United States", 37.619, -122.375, 3, demand=1.08),
        _ap("YYZ", "Toronto", "Canada", 43.677, -79.625, 3, demand=1.02),
        _ap("YUL", "Montréal", "Canada", 45.470, -73.741, 2, demand=1.00),
        _ap("YVR", "Vancouver", "Canada", 49.195, -123.184, 3, demand=1.03),
        _ap("MEX", "Mexico City", "Mexico", 19.436, -99.072, 3, demand=0.97),
        _ap("CUN", "Cancún", "Mexico", 21.037, -86.877, 2, "winter", 1.07),
        _ap("BOG", "Bogotá", "Colombia", 4.702, -74.147, 3, demand=0.95),
        _ap("GRU", "São Paulo", "Brazil", -23.436, -46.473, 3, demand=0.98),
        _ap("EZE", "Buenos Aires", "Argentina", -34.822, -58.536, 3, demand=0.97),
    ]
}

GERMAN = ("BER", "FRA", "MUC", "HAM", "DUS", "CGN", "STR", "HAJ", "NUE", "LEJ", "DRS", "BRE")
BEACH_EUROPE = ("PMI", "AGP", "ALC", "TFS", "LPA", "FAO", "NCE", "NAP", "CTA", "ATH", "HER", "LCA", "AYT")


@dataclass(frozen=True)
class Airline:
    code: str
    name: str
    kind: str  # "full-service", "low-cost" or "leisure"
    price: float  # price level relative to an average carrier
    bases: tuple[str, ...]  # hubs (full-service) or bases (low-cost / leisure)
    network: tuple[str, ...] = ()  # extra airports served from the bases (not used by full-service)
    max_range: float = 15000.0
    base_to_base: bool = True  # may fly between two of its own bases
    premium: bool = False  # sells Premium Economy (long-haul)
    business: bool = True
    first: bool = False


def _fsc(code, name, price, hubs, max_range=15000, premium=True, first=False):
    return Airline(code, name, "full-service", price, hubs, (), max_range, True, premium, True, first)


def _lcc(code, name, price, bases, network=(), max_range=4500, base_to_base=True, kind="low-cost",
         premium=False, business=False):
    return Airline(code, name, kind, price, bases, network, max_range, base_to_base, premium, business, False)


AIRLINES: dict[str, Airline] = {
    a.code: a
    for a in [
        # Full-service network carriers (fly non-stop from hubs, connect elsewhere)
        _fsc("LH", "Lufthansa", 1.15, ("FRA", "MUC"), 12000, first=True),
        _fsc("LX", "SWISS", 1.20, ("ZRH",), 11000, first=True),
        _fsc("OS", "Austrian Airlines", 1.08, ("VIE",), 9500),
        _fsc("BA", "British Airways", 1.17, ("LHR",), 12000, first=True),
        _fsc("AF", "Air France", 1.12, ("CDG",), 12000, first=True),
        _fsc("KL", "KLM", 1.08, ("AMS",), 12000),
        _fsc("IB", "Iberia", 1.00, ("MAD",), 11000),
        _fsc("AZ", "ITA Airways", 1.02, ("FCO",), 11000),
        _fsc("SK", "SAS", 1.02, ("CPH", "ARN", "OSL"), 9500),
        _fsc("AY", "Finnair", 1.00, ("HEL",), 11000),
        _fsc("TP", "TAP Air Portugal", 0.95, ("LIS",), 9500),
        _fsc("EI", "Aer Lingus", 0.96, ("DUB",), 9000),
        _fsc("A3", "Aegean Airlines", 0.92, ("ATH",), 3500, premium=False),
        _fsc("LO", "LOT Polish Airlines", 0.92, ("WAW",), 9500),
        _fsc("TK", "Turkish Airlines", 0.95, ("IST",), 14000),
        _fsc("EK", "Emirates", 1.10, ("DXB",), 14500, first=True),
        _fsc("QR", "Qatar Airways", 1.08, ("DOH",), 14500, first=True),
        _fsc("EY", "Etihad Airways", 1.02, ("AUH",), 14000, first=True),
        _fsc("LY", "El Al", 1.02, ("TLV",), 11500),
        _fsc("MS", "EgyptAir", 0.85, ("CAI",), 10000, premium=False),
        _fsc("KQ", "Kenya Airways", 0.95, ("NBO",), 9000, premium=False),
        _fsc("SA", "South African Airways", 0.98, ("JNB",), 11000, premium=False),
        _fsc("AI", "Air India", 0.88, ("DEL", "BOM"), 14000, first=True),
        _fsc("TG", "Thai Airways", 0.95, ("BKK",), 10500),
        _fsc("SQ", "Singapore Airlines", 1.15, ("SIN",), 16500, first=True),
        _fsc("MH", "Malaysia Airlines", 0.92, ("KUL",), 11000, premium=False),
        _fsc("CX", "Cathay Pacific", 1.08, ("HKG",), 14000, first=True),
        _fsc("CA", "Air China", 0.88, ("PEK",), 12000, first=True),
        _fsc("MU", "China Eastern", 0.85, ("PVG",), 12000),
        _fsc("KE", "Korean Air", 1.05, ("ICN",), 12500, first=True),
        _fsc("NH", "ANA", 1.12, ("HND",), 12500, first=True),
        _fsc("JL", "Japan Airlines", 1.10, ("HND",), 12500, first=True),
        _fsc("QF", "Qantas", 1.15, ("SYD", "MEL"), 15000, first=True),
        _fsc("UA", "United Airlines", 1.12, ("ORD", "SFO", "IAD"), 14000),
        _fsc("DL", "Delta Air Lines", 1.12, ("ATL", "JFK", "LAX"), 14000),
        _fsc("AA", "American Airlines", 1.10, ("MIA", "JFK", "ORD"), 13000, first=True),
        _fsc("AC", "Air Canada", 1.08, ("YYZ", "YUL", "YVR"), 13000),
        _fsc("AM", "Aeroméxico", 0.95, ("MEX",), 11000),
        _fsc("AV", "Avianca", 0.92, ("BOG",), 9500, premium=False),
        _fsc("LA", "LATAM Airlines", 0.95, ("GRU",), 11000),
        _fsc("AR", "Aerolíneas Argentinas", 0.92, ("EZE",), 11500, premium=False),
        # Low-cost carriers (point-to-point inside their network)
        _lcc("FR", "Ryanair", 0.58, (
            "BER", "CGN", "BRE", "NUE", "MAN", "EDI", "DUB", "BRU", "BCN", "MAD", "PMI", "AGP",
            "ALC", "TFS", "LPA", "LIS", "OPO", "FAO", "FCO", "MXP", "VCE", "NAP", "CTA", "ATH",
            "LCA", "WAW", "KRK", "BUD", "OTP", "SOF", "VIE", "PRG", "CPH", "RAK",
        ), max_range=4000),
        _lcc("U2", "easyJet", 0.66, (
            "LGW", "MAN", "EDI", "BER", "HAM", "CDG", "NCE", "LYS", "AMS", "BRU", "GVA", "MXP",
            "NAP", "VCE", "BCN", "MAD", "PMI", "AGP", "ALC", "TFS", "LPA", "LIS", "OPO", "FAO",
            "ATH", "HER", "LCA", "PRG", "BUD", "KRK", "CPH", "RAK", "HRG", "TLV", "CTA",
        ), max_range=4800),
        _lcc("W6", "Wizz Air", 0.55, ("BUD", "WAW", "KRK", "OTP", "SOF", "PRG", "VIE", "AUH"), (
            "LGW", "DUS", "DRS", "HAM", "FRA", "MUC", "BER", "DUB", "BCN", "MAD", "FCO", "MXP", "NAP",
            "CTA", "VCE", "LIS", "TLV", "LCA", "ATH", "CPH", "OSL", "DXB", "MLE", "PMI", "AGP", "TFS",
            "HRG", "CAI",
        ), max_range=5500),
        _lcc("VY", "Vueling", 0.70, ("BCN", "MAD", "PMI", "AGP"), (
            "FCO", "CDG", "AMS", "BER", "FRA", "MUC", "HAM", "DUS", "STR", "LGW", "ZRH", "GVA",
            "LIS", "OPO", "TFS", "LPA", "ALC", "NAP", "VCE", "ATH", "CPH", "PRG", "BRU", "RAK", "TLV",
        ), max_range=3800),
        _lcc("EW", "Eurowings", 0.78, ("DUS", "CGN", "HAM", "STR", "BER", "MUC", "HAJ", "NUE", "LEJ", "DRS"), (
            "VIE", "PMI", "AGP", "ALC", "TFS", "LPA", "FAO", "LIS", "OPO", "NCE", "BCN", "MAD",
            "FCO", "NAP", "CTA", "VCE", "MXP", "ATH", "HER", "LCA", "AYT", "IST", "HRG", "RAK",
            "LGW", "MAN", "EDI", "DUB", "CPH", "ARN", "OSL", "PRG", "KRK", "BUD", "SOF", "TLV", "ZRH", "BRU",
        ), max_range=4600),
        _lcc("PC", "Pegasus Airlines", 0.65, ("IST", "AYT"), (
            "BER", "FRA", "MUC", "HAM", "DUS", "CGN", "STR", "HAJ", "NUE", "LGW", "MAN", "AMS", "BRU",
            "CDG", "VIE", "ZRH", "BCN", "MAD", "FCO", "MXP", "ATH", "TLV", "CAI", "DXB", "DOH", "AUH",
            "CPH", "PRG", "WAW", "BUD",
        ), max_range=4500, base_to_base=False),
        _lcc("FZ", "flydubai", 0.72, ("DXB",), (
            "IST", "AYT", "ATH", "PRG", "WAW", "KRK", "BUD", "OTP", "SOF", "VIE", "NAP", "CTA", "MXP",
            "LCA", "TLV", "CAI", "NBO", "DEL", "BOM", "BLR", "MLE", "BKK", "KUL", "HEL", "OSL", "CPH",
        ), max_range=5500, business=True),
        _lcc("TR", "Scoot", 0.62, ("SIN",), (
            "BER", "ATH", "BKK", "KUL", "DPS", "HKG", "PVG", "ICN", "HND", "SYD", "MEL", "DEL", "BLR", "MLE",
        ), max_range=11000, premium=True),
        _lcc("AK", "AirAsia", 0.52, ("KUL", "BKK", "DPS"), (
            "SIN", "HKG", "PVG", "PEK", "ICN", "HND", "DEL", "BLR", "MLE", "SYD", "MEL",
        ), max_range=7000),
        _lcc("JQ", "Jetstar", 0.62, ("SYD", "MEL"), ("DPS", "BKK", "SIN", "HND", "ICN"), max_range=8500),
        _lcc("6E", "IndiGo", 0.62, ("DEL", "BOM", "BLR"), (
            "DXB", "AUH", "DOH", "IST", "BKK", "SIN", "KUL", "DPS", "MLE", "NBO", "AMS", "MAN",
        ), max_range=7500),
        _lcc("WN", "Southwest Airlines", 0.72, ("ATL", "ORD", "IAD", "BOS", "MIA", "LAX", "SFO"), ("CUN", "MEX"),
             max_range=4500),
        _lcc("B6", "JetBlue", 0.82, ("JFK", "BOS"), (
            "MIA", "LAX", "SFO", "IAD", "ORD", "CUN", "MEX", "BOG", "LHR", "CDG", "AMS", "DUB", "EDI", "MAD",
        ), max_range=6200, business=True),
        # Leisure carriers (from home bases to holiday and long-haul destinations)
        _lcc("DE", "Condor", 0.82, ("FRA", "MUC", "DUS", "HAM", "BER", "LEJ", "STR"), BEACH_EUROPE + (
            "TFS", "LPA", "PMI", "AGP", "HRG", "RAK", "JFK", "BOS", "IAD", "MIA", "LAX", "SFO", "YYZ",
            "YVR", "CUN", "MLE", "BKK", "CPT", "NBO", "DXB",
        ), max_range=10500, base_to_base=False, kind="leisure", premium=True, business=True),
        _lcc("X3", "TUI fly", 0.80, ("HAJ", "DUS", "FRA", "MUC", "STR", "HAM", "CGN", "NUE", "LEJ", "BER"),
             BEACH_EUROPE + ("HRG", "RAK", "TFS", "LPA", "FAO"), max_range=4800, base_to_base=False, kind="leisure"),
        _lcc("XQ", "SunExpress", 0.76, ("AYT", "IST"), GERMAN + ("VIE", "ZRH", "AMS", "CPH", "ARN", "OSL"),
             max_range=3500, base_to_base=False, kind="leisure"),
    ]
}

CABINS: dict[str, str] = {
    "economy": "Economy",
    "premium": "Premium Economy",
    "business": "Business",
    "first": "First",
}

TIME_SLOTS: dict[str, str] = {
    "early": "Early morning (00–06)",
    "morning": "Morning (06–12)",
    "afternoon": "Afternoon (12–17)",
    "evening": "Evening (17–21)",
    "night": "Night (21–24)",
}

STOPS: dict[int, str] = {0: "Non-stop", 1: "1 stop", 2: "2 stops"}

LONG_HAUL_KM = 3500  # premium cabins (Premium Economy) only exist above this distance
FIRST_CLASS_KM = 5000


@lru_cache(maxsize=None)
def distance_km(origin: str, destination: str) -> float:
    """Great-circle distance between two airports (haversine formula)."""
    a, b = AIRPORTS[origin], AIRPORTS[destination]
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def route_type(distance: float) -> str:
    if distance < 1500:
        return "short-haul"
    if distance < 4000:
        return "medium-haul"
    return "long-haul"
