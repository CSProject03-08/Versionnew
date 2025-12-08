"""This script generates seed trip data for our Business Trip application.

Swiss cities and towns are grouped into three cost tiers. For each generated
trip, the script selects an origin and a destination at random and assigns:
- a hotel cost based on real scraped example rates for the respective tier,
- a daily meal cost within the tier-specific range,
- and an estimated SBB ticket price derived from the geodesic distance.

The output is a CSV file (seed_trips.csv), which serves as the initial training dataset for the machine learning model.
"""

import random
from typing import Dict, Tuple, List, Optional

import pandas as pd
from geopy.distance import geodesic

from api.api_city_lookup import get_city_coords

# Tier 1 Cities: Swiss cities considered most expensive for seed data generation
TIER_1_CITIES = {
    "Zurich", "Geneva", "Basel", "Lausanne", "Zermatt", "St. Moritz",
    "Davos", "Klosters", "Verbier", "Gstaad", "Andermatt", "Grindelwald",
    "Wengen", "Mürren", "Saas-Fee", "Arosa", "Lenzerheide", "Flims", "Laax",
    "Engelberg", "Crans-Montana", "Montreux", "Lucerne", "Ascona", "Zug"
}

# Tier 2 Cities: Swiss cities considered moderately expensive for seed data generation
TIER_2_CITIES = {
    "Bern", "Winterthur", "St. Gallen", "Biel", "Schaffhausen",
    "Chur", "Thun", "Neuchâtel", "Fribourg", "Sion", "Brig", "Bellinzona",
    "Interlaken", "Kloten", "Lugano", "Locarno",
}

# Tier 3 Cities: Swiss cities considered least expensive for seed data generation
TIER_3_CITIES = {
    "Solothurn", "Olten", "Rapperswil", "Uster", "Baden", "Wil", "Arbon",
    "Romanshorn", "Spiez", "Steffisburg", "Villars-sur-Glâne", "Pfäffikon", "Wetzikon"
}

TIER_HOTEL_RATES = {
    "T1": [332.00, 203.00, 360.65, 223.75, 190.55, 169.80, 215.00],
    "T2": [214.00, 170.00, 176.00, 225.00, 174.20, 134.00, 116.00],
    "T3": [161.00, 179.00, 154.00, 223.50, 223.00, 150.00, 142.00],
}

TIER_BASELINES = {
    "T1": {"meals_min": 80.0, "meals_max": 100.0},
    "T2": {"meals_min": 75.0, "meals_max": 95.0},
    "T3": {"meals_min": 65.0, "meals_max": 85.0},
}

# Distance and SBB fares
_coords_cache: Dict[str, Tuple[float, float]] = {}

def get_tier(city: str) -> str:
    """
    Determines the cost tier of a given city.

    The function checks whether the city is listed in the Tier 1, Tier 2,
    or Tier 3 city sets and returns the corresponding tier label. Cities
    not found in any of the predefined sets are assigned to Tier 3 by default.

    Args:
        city (str): Name of the city.

    Returns:
        str: The tier label ("T1", "T2", or "T3") associated with the city.
    """
    if city in TIER_1_CITIES:
        return "T1"
    if city in TIER_2_CITIES:
        return "T2"
    if city in TIER_3_CITIES:
        return "T3"
    return "T3"

def get_coords_cached(city: str):
    """
    Returns coordinates for a city, using a simple caching mechanism to reduce repeated external lookups.

    Args:
        city: Name of the city.

    Returns:
        (latitude, longitude) tuple if the city can be resolved; otherwise None.
    """
    if city in _coords_cache:
        return _coords_cache[city]

    coords = get_city_coords(city)
    if coords is not None:
        _coords_cache[city] = coords
    return coords


def estimate_distance_and_ticket(origin: str, dest: str):
    """
    Computes the geodesic distance between two cities and estimates an SBB round-trip ticket price based on a linear cost model.

    Args:
        origin (str): Origin city.
        dest (str): Destination city.

    Returns:
        Tuple[float, float]: A tuple containing:
            - distance_km (float): Distance between the cities in kilometers.
            - ticket_cost (float): Estimated round-trip ticket price.

    Raises:
        ValueError: If coordinates for either city cannot be determined.
    """
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


# 3. Automatic random seed trips
ALL_CITIES: List[str] = sorted(TIER_1_CITIES | TIER_2_CITIES | TIER_3_CITIES)

NUM_TRIPS= 75

def generate_random_seed_trips():
    """
    Generates a dataset of synthetic business trips across all tiers.

    For each trip:
        - an origin city is selected from all cities,
        - a destination city is selected from all cities excluding the origin,
        - hotel costs are sampled from real example rates,
        - meal costs are sampled from the tier-specific range,
        - distance and ticket costs are computed.

    Returns:
        pd.DataFrame: A DataFrame containing the generated trip records.
    """
    rows = []

    for _ in range(NUM_TRIPS):
        origin = random.choice(ALL_CITIES)
        dest = random.choice([c for c in ALL_CITIES if c != origin])

        duration_days = random.randint(1, 5)
        tier_label = get_tier(dest)
        base = TIER_BASELINES[tier_label]

        # Pick a random real scraped rate for the tier
        nightly_hotel = random.choice(TIER_HOTEL_RATES[tier_label])
        nightly_hotel *= random.uniform(0.95, 1.05)

        hotel_cost = round(nightly_hotel * duration_days, 2)

        # meals
        meals_per_day = round(random.uniform(base["meals_min"], base["meals_max"]), 2)
        meals_cost = round(meals_per_day * duration_days, 2)

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
    print(f"Wrote {len(df)} seed trips to {output_path}")