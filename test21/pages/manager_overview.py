import streamlit as st
from db.db_functions_users import register_user_dropdown, del_user_dropdown, edit_user_dropdown
from db.db_functions_trips import create_trip_dropdown, del_trip_dropdown, create_trip_table, create_trip_users_table, trip_list_view
st.set_page_config(page_title="Manager Overview", layout="wide")
st.title("Manager Dashboard")
create_trip_table()
create_trip_users_table()

### Access control, so only managers can access this page ###
if "role" not in st.session_state or st.session_state["role"] != "Manager":
    st.error("Access denied. Please log in as Manager.")
    st.stop()

left, right = st.columns([4, 2], gap="large")

with right:
    st.subheader("User-Management")
    register_user_dropdown()
    edit_user_dropdown()
    del_user_dropdown()
    st. subheader("Trip-Management")
    create_trip_dropdown()
    del_trip_dropdown()

with left:
    st.subheader("Trip-Overview")
    trip_list_view()