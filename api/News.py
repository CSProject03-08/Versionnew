import sqlite3
import streamlit as st
import requests
from pathlib import Path

# --- Database connection ---
DB_PATH = Path(__file__).parent.parent / "db" / "users.db"

def connect():
    return sqlite3.connect(DB_PATH)


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
          AND t.end_date >= DATE('now')
        ORDER BY t.start_date ASC
    """

    rows = conn.execute(query, (user_id,)).fetchall()
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
def fetch_news_for_city(city_name: str):
    API_KEY = "ad63614ff90fc6ae7308e5cb4c0796d0"  # <-- your key

    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": API_KEY,
        "countries": "ch",
        "languages": "en",
        "keywords": city_name,
        "sort": "published_desc",
        "limit": 5
    }

    try:
        resp = requests.get(url, params=params)
        data = resp.json()

        if "data" not in data or not data["data"]:
            return []

        return data["data"]

    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []


# --- Display simple list-style news widget ---
def display_news_list(articles, city_name):
    st.subheader(f"📰 News for your trip to {city_name}")

    for article in articles:
        st.markdown(f"### {article.get('title', 'No title')}")
        st.write(article.get("description", "No description available."))
        st.write(f"**Source:** {article.get('source', 'Unknown')}")
        st.markdown(f"[Read full article]({article.get('url', '#')})")
        st.markdown("---")


# --- MAIN WIDGET: Works exactly like the weather widget ---
def news_widget():
    """
    Automatically loops through all upcoming user trips
    and shows news for each destination.
    Works exactly like your weather widget.
    """

    trips = get_upcoming_trips_for_user()

    if not trips:
        st.info("No upcoming trips found.")
        return

    for trip in trips:
        city = trip["destination"]

        st.markdown(f"### ✈ Destination: **{city}**")

        articles = fetch_news_for_city(city)

        if not articles:
            st.info(f"No news found for {city}.")
            st.markdown("---")
            continue

        display_news_list(articles, city)
        st.markdown("---")