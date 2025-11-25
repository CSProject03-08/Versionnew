import random
from typing import Dict, Tuple, List, Optional

import pandas as pd
from geopy.distance import geodesic

from api.api_city_lookup import get_city_coords


# -----------------------------
# 1. Tier definitions
# -----------------------------

TIER_1_CITIES = {
    "Zurich", "Geneva", "Basel", "Lausanne", "Zug", "Zermatt", "St. Moritz",
    "Davos", "Klosters", "Verbier", "Gstaad", "Andermatt", "Grindelwald",
    "Wengen", "Mürren", "Saas-Fee", "Arosa", "Lenzerheide", "Flims", "Laax",
    "Engelberg", "Crans-Montana", "Montreux", "Lucerne", "Lugano", "Ascona",
    "Locarno"
}

TIER_2_CITIES = {
    "Bern", "Winterthur", "St. Gallen", "Biel", "Biel/Bienne", "Schaffhausen",
    "Chur", "Thun", "Neuchâtel", "Fribourg", "Sion", "Brig", "Bellinzona",
    "Interlaken", "Kloten"
}

TIER_3_CITIES = {
    "Solothurn", "Olten", "Rapperswil", "Uster", "Baden", "Wil", "Arbon",
    "Romanshorn", "Spiez", "Steffisburg", "Villars-sur-Glâne", "Pfäffikon",
}


def get_tier(city: str) -> str:
    if city in TIER_1_CITIES: return "T1"
    if city in TIER_2_CITIES: return "T2"
    if city in TIER_3_CITIES: return "T3"
    return "T3"  # fallback


# baseline hotel per night & meal ranges per day by tier
TIER_BASELINES = {
    "T1": {"hotel_min": 203.0, "hotel_max": 332.0, "meals_min": 80.0, "meals_max": 100.0},
    "T2": {"hotel_min": 176.0, "hotel_max": 214.0, "meals_min": 75.0, "meals_max": 95.0},
    "T3": {"hotel_min": 161.0, "hotel_max": 179.0, "meals_min": 65.0, "meals_max": 85.0},
}


# -----------------------------
# 2. Distance + SBB seed fares
# -----------------------------

_coords_cache: Dict[str, Tuple[float, float]] = {}


def get_coords_cached(city: str) -> Optional[Tuple[float, float]]:
    if city in _coords_cache:
        return _coords_cache[city]

    coords = get_city_coords(city)
    if coords is not None:
        _coords_cache[city] = coords
    return coords


def estimate_distance_and_ticket(origin: str, dest: str) -> Tuple[float, float]:
    origin_coords = get_coords_cached(origin)
    dest_coords = get_coords_cached(dest)

    if origin_coords is None:
        raise ValueError(f"Could not resolve origin city '{origin}'.")
    if dest_coords is None:
        raise ValueError(f"Could not resolve destination city '{dest}'.")

    distance_km = geodesic(origin_coords, dest_coords).km

    base_fare = 5.0
    per_km = 0.40

    # Always round trip for seed data
    ticket_cost = (base_fare + per_km * distance_km) * 2

    return distance_km, ticket_cost


# -----------------------------
# 3. Automatic random seed trips
# -----------------------------

ALL_CITIES: List[str] = sorted(TIER_1_CITIES | TIER_2_CITIES | TIER_3_CITIES)

NUM_TRIPS_PER_TIER = {"T1": 25, "T2": 25, "T3": 25}


def generate_random_seed_trips() -> pd.DataFrame:
    rows = []

    tier_to_cities = {
        "T1": list(TIER_1_CITIES),
        "T2": list(TIER_2_CITIES),
        "T3": list(TIER_3_CITIES),
    }

    for tier_label, n_trips in NUM_TRIPS_PER_TIER.items():
        dest_candidates = tier_to_cities[tier_label]

        for _ in range(n_trips):
            origin = random.choice(ALL_CITIES)
            dest = random.choice(dest_candidates)

            if origin == dest and len(ALL_CITIES) > 1:
                origin = random.choice([c for c in ALL_CITIES if c != dest])

            duration_days = random.randint(1, 5)

            base = TIER_BASELINES[tier_label]

            # nightly hotel cost
            nightly_hotel = random.uniform(base["hotel_min"], base["hotel_max"])
            hotel_cost = nightly_hotel * duration_days

            # meals
            meals_per_day = random.uniform(base["meals_min"], base["meals_max"])
            meals_cost = meals_per_day * duration_days

            try:
                distance_km, ticket_cost = estimate_distance_and_ticket(origin, dest)
            except ValueError as e:
                print(f"Skipping trip {origin} -> {dest}: {e}")
                continue

            total_cost = hotel_cost + meals_cost + ticket_cost

            rows.append({
                "origin_city": origin,
                "dest_city": dest,
                "tier": tier_label,
                "duration_days": duration_days,
                "distance_km": round(distance_km, 2),
                "hotel_cost": round(hotel_cost, 2),
                "meals_per_day": round(meals_per_day, 2),
                "meals_cost": round(meals_cost, 2),
                "ticket_cost": round(ticket_cost, 2),
                "total_cost": round(total_cost, 2),
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_random_seed_trips()
    output_path = "seed_trips.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Wrote {len(df)} seed trips to {output_path}")
