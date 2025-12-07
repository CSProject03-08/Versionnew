import pyodbc
import streamlit as st
import requests
from pathlib import Path
from datetime import date
from sqlalchemy import create_engine

# The engine serves as a central gateway to the database (MS Azure SQL). 
# It manages the connections and translates Python commands into the appropriate SQL dialect.
# pandas requires this!
DATABASE_URI = st.secrets["azure_db"]["ENGINE"]
engine = create_engine(DATABASE_URI)

# Fetching for all information in the st.secrets and defining the connection string for the normal connection where pandas is not involved
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
    """Connects to Azure SQL-database.
    
    Args:
        None
        
    Returns:
        None
    """
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # show the error
        st.error(f"Connection error: {sqlstate}")
        return None


# --- Fetch upcoming trips for logged-in user ---
def get_upcoming_trips_for_user():
    if "user_ID" not in st.session_state:
        return []

    user_id = int(st.session_state["user_ID"])
    conn = connect()

    query = """
        SELECT t.trip_ID, t.origin, t.destination, t.start_date, t.end_date
        FROM trips t
        JOIN user_trips ut ON t.trip_ID = ut.trip_ID
        WHERE ut.user_ID = ?
          AND t.end_date >= ?
        ORDER BY t.start_date ASC
    """

    rows = conn.execute(query, (user_id, date.today())).fetchall()
    conn.close()

    # Convert rows to list of dicts
    return [
        {
            "trip_ID": r[0],
            "origin": r[1],
            "destination": r[2],
            "start_date": r[3],
            "end_date": r[4],
        }
        for r in rows
    ]


# --- Fetch news from Mediastack API ---
def fetch_news_for_city(destination: str):
    API_KEY = "ad63614ff90fc6ae7308e5cb4c0796d0"  # <-- your key

    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": API_KEY,
        "countries": "ch",
        "languages": "de",
        "keywords": destination,
        "sort": "published_desc",
        "limit": 5
    }

    try:
        resp = requests.get(url, params=params)
        st.write = type(resp)
        data = resp.json()

        if "data" not in data or not data["data"]:
            return []

        return data["data"][0]["title"]

    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []

# --- Display simple list-style news widget ---
def display_news_list(articles, destination):
    st.subheader(f"📰 News for your trip to {destination}")

    for article in articles:
        st.markdown(f"### {article.get('title', 'No title')}")
        st.write(article.get("description", "No description available."))
        st.write(f"**Source:** {article.get('source', 'Unknown')}")
        st.markdown(f"[Read full article]({article.get('url', '#')})")
        st.markdown("---")


# --- MAIN WIDGET: Works exactly like the weather widget ---
def news_widget(destination: str):
    """
    Automatically loops through all upcoming user trips
    and shows news for each destination.
    Works exactly like your weather widget.
    """

    if not destination:
        st.info("City to search for news.")
        return


    st.markdown(f"### ✈ Destination: **{destination}**")

    articles = fetch_news_for_city(destination)

    if not articles:
        st.info(f"No news found for {destination}.")

    else:
        display_news_list(articles, destination)