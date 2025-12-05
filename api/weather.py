import pyodbc
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path

#BASE_DIR = Path(__file__).resolve().parent.parent / "db"   # geht aus api/ eine Ebene hoch nach Projektroot und dann in db/
#DB_PATH = BASE_DIR / "users.db"
#BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # .../db
#DB_PATH  = os.path.join(BASE_DIR, "users.db")

SERVER_NAME = st.secrets["azure_db"]["SERVER_NAME"]
DATABASE_NAME = st.secrets["azure_db"]["DATABASE_NAME"]
USERNAME = st.secrets["azure_db"]["USERNAME"]
PASSWORD = st.secrets["azure_db"]["PASSWORD"]

CONNECTION_STRING = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    f'SERVER={SERVER_NAME};'
    f'DATABASE={DATABASE_NAME};'
    f'UID={USERNAME};'
    f'PWD={PASSWORD};'
    'Encrypt=yes;'  
    'TrustServerCertificate=no;'
)

def connect():
    """Connects to Azure SQL-database"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # show the error
        st.error(f"Connection error: {sqlstate}")
        return None

### Connecting to the database users.db ###
#def connect():
    #return sqlite3.connect(DB_PATH)

# --- Add Versionnew/ to Python path for imports ---
project_root = Path(__file__).parent.parent  # Goes to Versionnew/
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Helper function to fetch upcoming trips for a user ---
def get_upcoming_trips_for_user():

    if "user_ID" not in st.session_state:
        st.warning("User is not logged in.")
        return []
    
    user_id = int(st.session_state["user_ID"])

    try:
        conn = connect()
        if conn is None:
            return []
        

        query = """
            SELECT t.trip_ID, t.origin, t.destination, t.start_date, t.end_date
            FROM trips t
            JOIN user_trips ut ON t.trip_ID = ut.trip_ID
            WHERE ut.user_ID = ?
            AND t.end_date >= CAST(GETDATE() AS DATE)
            ORDER BY t.start_date ASC
        """
        c = conn.cursor()
        rows = c.execute(query, (user_id,)).fetchall()
        columns = [description[0] for description in c.description]
        return [dict(zip(columns, row)) for row in rows]
        #rows = conn.execute(query, (user_id,)).fetchall()
        #columns = [col[0] for col in conn.execute("PRAGMA table_info(trips)").fetchall()]
        #conn.close()
        #return [dict(zip(columns, row)) for row in rows]
    except pyodbc.Error as e:
        st.error(f"Database query failed when fetching trips: {e}")
        return []
        
    except Exception as e:
        # catches every error
        st.error(f"An unexpected error occurred: {e}")
        return []
        
    finally:
        if conn:
            conn.close()

# --- Main weather widget ---
def weather_widget(username: str = None):
    """
    Display upcoming trips and weather forecast for a given user.
    If username is None, uses the current logged-in user from session_state.
    """
    #user_id = int(st.session_state["user_ID"])

    #st.subheader("Weather Forecast")
    upcoming_trips = get_upcoming_trips_for_user()

    if not upcoming_trips:
        st.info("No upcoming trips found.")
        return

    for trip in upcoming_trips:
        city_name = trip['destination']
        start_date = trip['start_date']
        end_date = trip['end_date']

        # --- Geocoding ---
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}"
            geo_resp = requests.get(geo_url).json()
            if "results" not in geo_resp or len(geo_resp["results"]) == 0:
                st.warning(f"Could not find coordinates for {city_name}.")
                continue

            lat = geo_resp["results"][0]["latitude"]
            lon = geo_resp["results"][0]["longitude"]

        except requests.exceptions.RequestException as e:
            st.error(f"Geocoding request failed: {e}")
            continue

        # --- Weather Request ---
        try:
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

        except requests.exceptions.RequestException as e:
            st.error(f"Weather API request failed: {e}")
            continue

        # --- Display Trip Info ---
        #st.markdown(f"### ✈️ {city_name} ({start_date} → {end_date})")

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
