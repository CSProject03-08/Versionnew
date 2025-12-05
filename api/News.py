import streamlit as st
import requests
import json
import streamlit.components.v1 as components
from db.db_functions_users import edit_own_profile
from db.db_functions_trips import get_upcoming_trips_for_user

# --- Fetch news for a given city using Mediastack API ---
def fetch_news_for_city(city_name: str):
    """
    Fetch top Swiss news in English for a given city.
    """
    API_KEY = "ad63614ff90fc6ae7308e5cb4c0796d0"  # <-- Insert your API key here
    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": API_KEY,
        "countries": "ch",  # Switzerland
        "languages": "en",
        "keywords": city_name,
        "sort": "published_desc",
        "limit": 10
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

# --- Display news as a rotating carousel ---
def news_carousel(articles, city_name):
    """
    Show news articles in a carousel with previous/next buttons and auto-rotate every 5 seconds.
    """
    articles_json = json.dumps(articles)
    html_code = f"""
    <div id="carousel-container" style="
        width: 100%;
        border: 1px solid #ccc;
        padding: 20px;
        border-radius: 12px;
        background: #f9f9f9;
        font-family: Arial;
    ">
        <h3 style="text-align: center; margin-top: 0;">📰 Regional News from {city_name}</h3>
        <div id="news-content" style="min-height: 150px; margin-bottom: 20px;"></div>
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

# --- Widget for a single trip ---
def news_widget_for_trip(city_name: str):
    """
    Fetch and display news for a given city.
    """
    st.subheader(f"📰 News for your trip to {city_name}")
    articles = fetch_news_for_city(city_name)
    if not articles:
        st.info(f"No news found for {city_name}.")
        return
    news_carousel(articles, city_name)

# --- Main News Widget (like the weather widget) ---
def news_widget():
    """
    Loops through the user's upcoming trips and displays news for each trip.
    Also shows the profile editor on top.
    """
    # Display profile editor
    edit_own_profile()

    st.subheader("Regional News for Your Trips")

    # Get user's trips
    user_id = st.session_state.get("user_ID")
    if not user_id:
        st.info("No user logged in.")
        return

    upcoming_trips = get_upcoming_trips_for_user(user_id)
    if not upcoming_trips:
        st.info("No upcoming trips found.")
        return

    # Show news for each trip
    for trip in upcoming_trips:
        city_name = trip['destination']
        news_widget_for_trip(city_name)
