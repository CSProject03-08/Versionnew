import requests

def get_swiss_weather(lat, lon):
    url = "https://data.geo.admin.ch/api/stac/v0.9/collections/ch.meteoschweiz.ogd-local-forecasting/items"
    params = {"bbox": f"{lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}", "limit": 1}
    res = requests.get(url, params=params)
    res.raise_for_status()
    data = res.json()
    if data.get("features"):
        props = data["features"][0]["properties"]
        return {
            "timestamp": props.get("time"),
            "temperature": props.get("T_2M"),
            "precipitation": props.get("TOT_PRECIP"),
            "wind_speed": props.get("WIND_SPEED")
        }
    return None
