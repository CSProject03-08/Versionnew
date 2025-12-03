import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import date
from db.db_functions_users import edit_own_profile
from db.db_functions_employees import employee_listview, past_trip_view_employee
from api.Weather import weather_widget

DB_PATH = "db/users.db"


st.set_page_config(page_title="User Dashboard", layout="wide")
st.title("User Dashboard")

### Access control, so only users can access this page ###
if "role" not in st.session_state or st.session_state["role"] != "User":
    st.error("Access denied. Please log in as User.")
    st.stop()


left, right = st.columns([4, 2], gap="large")
with left:
    st.subheader("Trip-Overview")
    employee_listview()
    past_trip_view_employee()


with right:
    edit_own_profile()
    st.subheader("Weather Forecast for Your Trips")
    weather_widget(st.session_state.get("username"))