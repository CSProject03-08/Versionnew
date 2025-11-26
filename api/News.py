### API for News and User Dashboard Page ###

import streamlit as st
import requests
from datetime import date
from db.db_functions_users import edit_own_profile
from db.db_functions_employees import employee_listview

DB_PATH = "db/users.db"
API_KEY = "ttps://api.worldnewsapi.com/top-news?source-country=ch" 

# Swiss News Carousel Widget #
def get_swiss_news_english():
    """Fetch today's Swiss news in English from World News API."""
    today = date.today().strftime("%Y-%m-%d")
    url = f"https://api.worldnewsapi.com/top-news?source-country=ch&language=en&date={today}"
    headers = {"x-api-key": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Error: {response.status_code}"}

def swiss_news_carousel_widget(container):
    """
    Display a Swiss news carousel inside a Streamlit container.
    Shows one article at a time, auto-swiping every 5 seconds.
    """
    # Initialize count in session state #
    if "news_index" not in st.session_state:
        st.session_state.news_index = 0

    data = get_swiss_news_english()

    if "error" in data:
        container.error(data["error"])
        return

    articles = data.get("news", []) or data.get("top_news", [])
    if not articles:
        container.warning("No news found for today.")
        return

    total_articles = len(articles)
    index = st.session_state.news_index % total_articles
    article = articles[index]

    # Display the current article #
    container.subheader(article.get("title", "No title"))
    container.write(article.get("text", ""))
    if "url" in article:
        container.markdown(f"[Read full article]({article['url']})")
    container.markdown("---")
    container.caption(f"Showing article {index + 1} of {total_articles}")

    # Auto-increment index every 5 seconds #
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = 0

    import time
    current_time = time.time()
    if current_time - st.session_state.last_refresh > 5:
        st.session_state.news_index += 1
        st.session_state.last_refresh = current_time
        st.experimental_rerun()

### User Dashboard Page ###

st.set_page_config(page_title="User Dashboard", layout="wide")
st.title("User Dashboard")

# Access control: only Users can access #
if "role" not in st.session_state or st.session_state["role"] != "User":
    st.error("Access denied. Please log in as User.")
    st.stop()

# Layout Columns #
left, right = st.columns([4, 2], gap="large")

with left:
    st.subheader("Trip-Overview")
    employee_listview()

with right:
    st.subheader("Your Profile")
    edit_own_profile()

    # Embed Swiss news carousel below the profile editor #
    st.subheader("🇨🇭 Swiss News (English)")
    news_widget_container = st.container()
    swiss_news_carousel_widget(news_widget_container)