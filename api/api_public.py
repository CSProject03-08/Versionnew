import streamlit
import requests
from datetime import datetime
import json
from db.sbb_stations import locations

BASE_URL = "https://api.opentransportdata.swiss/timetable/v1"

class SBBPublicClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_connections(self, from_station: str, to_station: str, date, time):
        """
        Query: https://api.opentransportdata.swiss/timetable/v1/connections
        Docs: https://opentransportdata.swiss/
        """

        url = "https://api.opentransportdata.swiss/ojp20/connections"

        params = {
            "from": from_station,
            "to": to_station,
            "date": date.strftime("%Y-%m-%d"),
            "time": time.strftime("%H:%M"),
            "limit": 4,       # number of connections returned
            "direct": 0,      # allow transfers
            "transportations": "train"  # only trains
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            raise Exception(
                f"[SBB API ERROR] {response.status_code} — {response.text}"
            )

        return response.json()

    def extract_travel_time(self, connection):
        """Return total travel time in minutes from a timetable connection."""
        duration = connection["duration"]  # format "01:34:00"
        h, m, _ = duration.split(":")
        return int(h) * 60 + int(m)

def get_sbb_connections(self, trip_row):
    sbb = SBBPublicClient(streamlit.secrets["sbb_api_key"])

    dep_station = locations[trip_row["departure_location"]]["station_id"]
    arr_station = locations[trip_row["destination"]]["station_id"]

    dt = datetime.strptime(trip_row["departure_time"], "%Y-%m-%d %H:%M:%S")

    return sbb.get_connections(
        from_station=dep_station,
        to_station=arr_station,
        date=dt.date(),
        time=dt.time()
    )