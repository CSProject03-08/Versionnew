import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# --- Add project root to Python path for imports ---
# The db folder is in test21/, so we need test21/ as the root
project_root = Path(__file__).parent.parent  # Goes to test21/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Import existing database modules ---
from db import db_functions_trips as db_trips


def weather_widget(employee_name: str = None):
    """
    Reusable weather widget that displays weather forecast for employee trips.
    
    Args:
        employee_name: Name of the employee to fetch trips for
    """
    if not employee_name:
        st.info("No employee selected. Please log in first.")
        return
    
    st.subheader("🛫 Your Upcoming Trips and Weather Forecast")
    
    # TODO: Implement actual trip fetching from db
    # For now, this is a placeholder. You'll need to implement:
    # upcoming_trips = db_trips.get_upcoming_trips_for_user(employee_name)
    upcoming_trips = []
    
    if not upcoming_trips:
        st.info("No upcoming trips found.")
        return
    
    for trip in upcoming_trips:
        trip_dict = dict(trip)
        city_name = trip_dict.get('destination')
        departure = trip_dict.get('departure_time')
        arrival = trip_dict.get('arrival_time')

        start_date = departure.strftime("%Y-%m-%d")
        end_date = arrival.strftime("%Y-%m-%d")

        # --- GEOCODING ---
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}"
        geo_resp = requests.get(geo_url).json()
        if "results" not in geo_resp or len(geo_resp["results"]) == 0:
            st.warning(f"Could not find coordinates for {city_name}.")
            continue

        lat = geo_resp["results"][0]["latitude"]
        lon = geo_resp["results"][0]["longitude"]

        # --- WEATHER REQUEST ---
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ["temperature_2m_max", "temperature_2m_min", "rain_sum", "snowfall_sum", "precipitation_probability_max"],
            "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "rain", "wind_speed_10m"],
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

        # --- HOURLY WEATHER (optional) ---
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


# --- Example usage (for testing) ---
if __name__ == "__main__":
    st.set_page_config(page_title="Weather Widget Test", layout="wide")
    st.title("Weather Widget Test")
    
    # Test the widget with a sample employee
    test_employee = st.text_input("Enter employee name (for testing):", "John Smith")
    weather_widget(test_employee)
    