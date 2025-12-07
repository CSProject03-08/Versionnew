"""Api_city_lookup.py contains two functions who return the longitude and latitude of the provided city name."""

import requests
from typing import Optional, Tuple, Dict, Any

# Nominatim (OpenStreetMap) endpoint
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Nominatim requires a valid User-Agent with contact info
HEADERS = {
    "User-Agent": "HorizonTravelApp/1.0 (schirin.salih@student.unisg.ch)"
}


def search_city(city_name: str, country: str = "Switzerland") -> Optional[Dict[str, Any]]:
    """
    Look up a city using the free Nominatim (OpenStreetMap) API.

    Args:
        city_name: Name of the city, e.g. "Zurich".
        country: Optional country filter, default "Switzerland".

    Returns:
        dict with the first match (includes 'lat', 'lon', 'display_name', etc.),
        or None if no result is found.
    """
    query = f"{city_name}, {country}" if country else city_name

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }

    resp = requests.get(
        NOMINATIM_URL,
        params=params,
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()

    if not results:
        return None

    return results[0]


def get_city_coords(city_name: str, country: str = "Switzerland") -> Optional[Tuple[float, float]]:
    """
    Convenience helper to directly get (lat, lon) for a city.

    Args:
        city_name: Name of the city, e.g. "Zurich".
        country: Optional country filter, default "Switzerland".

    Returns:
        (latitude, longitude) as floats, or None if the city was not found.
    """
    result = search_city(city_name, country=country)
    if not result:
        return None

    lat = float(result["lat"])
    lon = float(result["lon"])
    return lat, lon
