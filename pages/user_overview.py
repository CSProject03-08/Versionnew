"""user_overview.py contains the structure of the user overview. All necessary funcions are
imported from db_functions_users.py or db_functions_employees.py."""

import streamlit as st
from db.db_functions_users import edit_own_profile
from db.db_functions_employees import employee_listview, past_trip_view_employee
from api.News import news_widget
from utils import logout, hide_sidebar

st.set_page_config(page_title="User Dashboard", layout="wide")
left2, right2 = st.columns([5, 1], gap="large")
with left2:
    st.title("User Dashboard")
with right2:
    logout()

hide_sidebar()

# Access control, so only users can access this page
if "role" not in st.session_state or st.session_state["role"] != "User":
    st.error("Access denied. Please log in as User.")
    st.stop()

left, right = st.columns([4, 2], gap="large")
with left:
    st.subheader("Trip-Overview")
    employee_listview()
    past_trip_view_employee()

with right:
    logout()
    edit_own_profile()