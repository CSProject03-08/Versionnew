import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# --- Add Versionnew/ to Python path for imports ---
project_root = Path(__file__).parent.parent  # Goes to Versionnew/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Import database functions ---
from db import db_functions_trips as db_trips
from db import db_functions_employees as db_employees

# --- Helper function to fetch upcoming trips for a user ---
def get_upcoming_trips_for_user(user_id: int):
    conn = db_trips.connect()
    query = """
        SELECT t.trip_ID, t.origin, t.destination, t.start_date, t.end_date
        FROM trips t
        JOIN user_trips ut ON t.trip_ID = ut.trip_ID
        WHERE ut.user_ID = ?
          AND t.end_date >= DATE('now')
        ORDER BY t.start_date ASC
    """
    rows = conn.execute(query, (user_id,)).fetchall()
    columns = [col[0] for col in conn.execute("PRAGMA table_info(trips)").fetchall()]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

# --- Main weather widget ---
def weather_widget(username: str = None):
    """
    Display upcoming trips and weather forecast for a given user.
    If username is None, uses the current logged-in user from session_state.
    """
    # Determine user_id
    if username:
        # Lookup user_ID from username
        conn = db_trips.connect()
        user_row = conn.execute("SELECT user_ID FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if not user_row:
            st.warning(f"Username '{username}' not found.")
            return
        user_id = user_row[0]
    else:
        user_id = st.session_state.get("user_ID")
        if not user_id:
            st.info("No user logged in.")
            return

    st.subheader("🛫 Upcoming Trips & Weather Forecast")
    upcoming_trips = get_upcoming_trips_for_user(user_id)

    if not upcoming_trips:
        st.info("No upcoming trips found.")
        return

    for trip in upcoming_trips:
        city_name = trip['destination']
        start_date = trip['start_date']
        end_date = trip['end_date']

        # --- Geocoding ---
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}"
        geo_resp = requests.get(geo_url).json()
        if "results" not in geo_resp or len(geo_resp["results"]) == 0:
            st.warning(f"Could not find coordinates for {city_name}.")
            continue

        lat = geo_resp["results"][0]["latitude"]
        lon = geo_resp["results"][0]["longitude"]

        # --- Weather Request ---
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ["temperature_2m_max", "temperature_2m_min",
                      "rain_sum", "snowfall_sum", "precipitation_probability_max"],
            "hourly": ["temperature_2m", "relative_humidity_2m",
                       "precipitation", "rain", "wind_speed_10m"],
            "timezone": "auto"
        }
        weather_resp = requests.get(weather_url, params=params).json()

        # --- Display Trip Info ---
        st.markdown(f"### ✈️ {city_name} ({start_date} → {end_date})")

        # --- DAILY WEATHER ---
        if "daily" in weather_resp:
            daily = weather_resp["daily"]
            daily_df = pd.DataFrame({
                "Date": daily["time"],
                "Temp Max (°C)": daily["temperature_2m_max"],
                "Temp Min (°C)": daily["temperature_2m_min"],
                "Rain (mm)": daily["rain_sum"],
                "Snow (mm)": daily["snowfall_sum"],
                "Precip Probability (%)": daily["precipitation_probability_max"]
            })
            st.write("#### Daily Forecast")
            st.dataframe(daily_df)

            # Plot daily max/min temperatures
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(daily_df["Date"], daily_df["Temp Max (°C)"], label="Max Temp", marker='o')
            ax.plot(daily_df["Date"], daily_df["Temp Min (°C)"], label="Min Temp", marker='o')
            ax.set_xlabel("Date")
            ax.set_ylabel("Temperature (°C)")
            ax.set_title(f"Daily Temperatures for {city_name}")
            ax.legend()
            ax.grid(True)
            st.pyplot(fig)

        # --- HOURLY WEATHER ---
        if "hourly" in weather_resp:
            hourly = weather_resp["hourly"]
            hourly_df = pd.DataFrame({
                "Time": hourly["time"],
                "Temp (°C)": hourly["temperature_2m"],
                "Humidity (%)": hourly["relative_humidity_2m"],
                "Precipitation (mm)": hourly["precipitation"],
                "Rain (mm)": hourly["rain"],
                "Wind Speed (m/s)": hourly["wind_speed_10m"]
            })
            st.write("#### Hourly Forecast (next 48h)")
            st.dataframe(hourly_df.head(48))  # first 48h only

# --- Run widget for testing ---
if __name__ == "__main__":
    st.set_page_config(page_title="Weather Widget Test", layout="wide")
    st.title("Weather Widget Test")
    test_username = st.text_input("Enter username for testing:", "")
    weather_widget(test_username if test_username else None)
