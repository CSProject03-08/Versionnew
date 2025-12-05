import sqlite3
import streamlit as st
import requests
import json
import streamlit.components.v1 as components

# Fetch news for a given city
def fetch_news_for_city(city_name: str):
    """
    Fetch regional Swiss news for a given city.
    Uses Mediastack API (free tier available).
    """

    API_KEY = "ad63614ff90fc6ae7308e5cb4c0796d0"   # <<--- INSERT YOUR KEY HERE

    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": API_KEY,
        "countries": "ch",           # Switzerland
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


# Carousel component (HTML + JS)
def news_carousel(articles, city_name):
    """
    Display news articles in a rotating carousel.
    Auto-rotates every 5 seconds.
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

        <h3 style="text-align: center; margin-top: 0;">
            📰 Regional News from {city_name}
        </h3>

        <div id="news-content" style="
            min-height: 150px;
            margin-bottom: 20px;
            text-align: left;
        ">
        </div>

        <div style="display: flex; justify-content: space-between;">
            <button id="prev" style="
                padding: 8px 14px;
                border-radius: 6px;
                border: none;
                background: #ddd;
                cursor: pointer;
            ">◀ Previous</button>

            <button id="next" style="
                padding: 8px 14px;
                border-radius: 6px;
                border: none;
                background: #ddd;
                cursor: pointer;
            ">Next ▶</button>
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

        // Auto-rotate every 5 seconds
        setInterval(function() {{
            index = (index + 1) % articles.length;
            renderArticle();
        }}, 5000);

        // Initial load
        renderArticle();
    </script>
    """

    components.html(html_code, height=350)

# News widget for each trip
def news_widget_for_trip(city_name: str):
    """
    Displays a news carousel for the destination city of a trip.
    """

    st.subheader(f"📰 News for your trip to {city_name}")

    articles = fetch_news_for_city(city_name)

    if not articles:
        st.info(f"No news found for {city_name}.")
        return

    news_carousel(articles, city_name)
