import requests, os

BASE_URL = "https://smapi-travel-transport.api.sbb.ch"

def get_access_token():
    tenant_id = os.getenv("SBB_TENANT_ID")
    client_id = os.getenv("SBB_CLIENT_ID")
    client_secret = os.getenv("SBB_CLIENT_SECRET")
    scope = os.getenv("SBB_SCOPE")
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    res = requests.post(url, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
        "grant_type": "client_credentials"
    })
    res.raise_for_status()
    return res.json()["access_token"]

def get_trip_options(token, from_id="8503000", to_id="8507000"):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "segment_keys": [{
            "from_ticketing_stop_time_id": from_id,
            "to_ticketing_stop_time_id": to_id,
            "service_date": {"year": 2025, "month": 11, "day": 7},
            "boarding_time": {"year": 2025, "month": 11, "day": 7, "hours": 9, "minutes": 0},
            "arrival_time": {"year": 2025, "month": 11, "day": 7, "hours": 10, "minutes": 10}
        }]
    }
    res = requests.post(f"{BASE_URL}/v1/trip-options", headers=headers, json=body)
    res.raise_for_status()
    return res.json()
