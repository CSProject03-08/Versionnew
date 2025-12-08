"""manager_overview.py contains the structure of the manager overview. All necessary funcions are
imported from db_functions_users.py, db_functions_trips.py and create_trip_dropdown.py."""

import streamlit as st
from db.db_functions_users import register_user_dropdown, del_user_dropdown, edit_user_dropdown
from db.db_functions_trips import del_trip_dropdown, create_trip_table, create_trip_users_table, trip_list_view, past_trip_list_view, del_trip_forever
from db.create_trip_dropdown import create_trip_dropdown
from utils import logout, hide_sidebar

st.set_page_config(page_title="Manager Overview", layout="wide")
hide_sidebar()
left2, right2 = st.columns([5, 1], gap="large")
with left2:
    st.title("Manager Dashboard")
with right2:
    logout()

create_trip_table()
create_trip_users_table()

# Access control, so only managers can access this page
if "role" not in st.session_state or st.session_state["role"] != "Manager":
    st.error("Access denied. Please log in as Manager.")
    st.stop()

left, right = st.columns([4, 2], gap="large")

with right:
    st.subheader("User-Management")
    register_user_dropdown()
    edit_user_dropdown()
    del_user_dropdown()

with left:
    st.subheader("Trip-Overview")
    trip_list_view()
    past_trip_list_view()
    del_trip_forever()
    st. subheader("Trip-Management")
    create_trip_dropdown()
    del_trip_dropdown()