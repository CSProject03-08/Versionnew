"""News.py contains the news visualization for the employee."""

import pyodbc
import streamlit as st
import requests
from pathlib import Path
from datetime import date
from sqlalchemy import create_engine
from utils import load_secrets
import urllib

CONNECTION_STRING = load_secrets()
connect_uri = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(CONNECTION_STRING)
engine = create_engine(connect_uri, fast_executemany=True)

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


# --- Fetch news from Mediastack API ---
def fetch_news_for_city(destination: str):
    """Fetches news articles for a given city using the Mediastack API.
    
    Args:
        destination (str): The city to fetch news for.
        
    Returns:
        list of tuples: Each tuple contains (title, description) of a news article.
    """
    API_KEY = "4bc3d6b800ed57d36c23e74cd911f56a"

    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": API_KEY,
        "countries": "ch",
        "languages": "de",
        "keywords": destination,
        "sort": "published_desc",
        "limit": 3
    }

    try:
        resp = requests.get(url, params=params)
        data = resp.json()

        # falls nichts zurückkommt
        if "data" not in data or not data["data"]:
            return []

        articles = []
        for item in data["data"][:3]:
            title = item.get("title", "Ohne Titel")
            desc = item.get("description", "Keine Beschreibung verfügbar.")
            articles.append((title, desc))

        return articles

    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []


def news_widget(destination: str):
    """This function displays news articles for a given destination city in each expander
    in the employee list view.
    
    Args:
        destination (str): The destination city for which to fetch and display news.
        
    Returns:
        None
    """
    if not destination:
        st.info("Bitte gib eine Stadt ein, zu der News gesucht werden sollen.")
        return

    news = fetch_news_for_city(destination)

    if not news:
        st.info(f"No news found for {destination}.")
        return

    st.subheader(f"News for your trip to: {destination}")

    # display eacht title and description
    for i, (title, description) in enumerate(news, start=1):
        # title
        st.markdown(f"**{i}. {title}**")
        # description
        st.write(description)

        # thin separator between articles
        if i < len(news):
            st.markdown("---")
