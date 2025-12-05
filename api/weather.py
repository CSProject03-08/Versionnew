import streamlit as st
import requests
import json
from pathlib import Path
import sqlite3
import streamlit.components.v1 as components

# --- Database connection ---
DB_PATH = Path(__file__).parent.parent / "db" / "users.db"

def connect():
    return sqlite3.connect(DB_PATH)

# --- Helper to fetch upcoming trips for the logged-in user ---
def get_upcoming_trips_for_user():
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
    columns = [col[0] for col in conn.execute("PRAGMA table_info(trips)").fetchall()]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

# --- Fetch news from Mediastack API ---
def fetch_news_for_city(city_name: str):
    API_KEY = "YOUR_MEDIASTACK_API_KEY"  # <-- replace with your key
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
        if "data" not in data or len(data["data"]) == 0:
            return []
        return data["data"]
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []

# --- News carousel component ---
def news_carousel(articles, city_name):
    articles_json = json.dumps(articles)
    html_code = f"""
    <div id="carousel-container" style="width: 100%; border: 1px solid #ccc; padding: 20px; border-radius: 12px; background: #f9f9f9; font-family: Arial;">
        <h3 style="text-align: center; margin-top: 0;">📰 Regional News from {city_name}</h3>
        <div id="news-content" style="min-height: 150px; margin-bottom: 20px; text-align: left;"></div>
        <div style="display: flex; justify-content: space-between;">
            <button id="prev" style="padding: 8px 14px; border-radius: 6px; border: none; background: #ddd; cursor: pointer;">◀ Previous</button>
            <button id="next" style="padding: 8px 14px; border-radius: 6px; border: none; background: #ddd; cursor: pointer;">Next ▶</button>
        </div>
    </div>
    <script>
        const articles = {articles_json};
        let index = 0;
        function renderArticle() {{
            const a = articles[index];
            document.getElementById("news-content").innerHTML = `
                <h4>${{a.title}}</h4>
                <p><strong>Source:</strong> ${{a.source || "Unknown"}}</p>
                <p>${{a.description || ""}}</p>
                <a href="${{a.url}}" target="_blank">Read full article</a>
            `;
        }}
        document.getElementById("prev").onclick = function() {{
            index = (index - 1 + articles.length) % articles.length;
            renderArticle();
        }};
        document.getElementById("next").onclick = function() {{
            index = (index + 1) % articles.length;
            renderArticle();
        }};
        setInterval(function() {{
            index = (index + 1) % articles.length;
            renderArticle();
        }}, 5000);
        renderArticle();
    </script>
    """
    components.html(html_code, height=350)

# --- Main news widget for all trips ---
def news_widget():
    """
    Loops through all upcoming trips for the logged-in user
    and displays a news carousel for each trip destination.
    """
    upcoming_trips = get_upcoming_trips_for_user()
    if not upcoming_trips:
        st.info("No upcoming trips found.")
        return

    for trip in upcoming_trips:
        city_name = trip["destination"]
        articles = fetch_news_for_city(city_name)
        if not articles:
            st.info(f"No news found for {city_name}.")
            continue
        st.subheader(f"📰 News for your trip to {city_name}")
        news_carousel(articles, city_name)
