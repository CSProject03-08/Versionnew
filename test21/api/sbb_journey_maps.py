import requests

BASE_URL_MAPS = "https://smapi-journey-maps.api.sbb.ch"

def get_journey_map_image(token, booking_token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "image/png"}
    url = f"{BASE_URL_MAPS}/v1/journey-maps/{booking_token}"
    res = requests.get(url, headers=headers, params={"width": 600, "height": 400})
    if res.status_code == 200:
        return res.content
    return None
