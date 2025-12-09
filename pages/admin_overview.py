"""admin_overview.py contains the structure of the admin overview. All necessary funcions are
imported from db_functions_users.py."""

import streamlit as st
import pandas as pd
from db.db_functions_users import register_user_dropdown_admin, edit_user_dropdown_admin, get_users_under_me, del_user_dropdown_admin
from utils import hide_sidebar, logout 


st.set_page_config(page_title="Admin Dashboard", layout="wide")
hide_sidebar()
left2, right2 = st.columns([5, 1], gap="large")
with left2:
    st.title("Admin Dashboard")
with right2:
    logout()

# Access control, so only admin can access this page
if "role" not in st.session_state or st.session_state["role"] != "Administrator":
    st.error("Access denied. Please log in as Administrator.")
    st.stop()


left, right = st.columns([4, 2], gap="large")
with left:
    st.subheader("Table")
    df = get_users_under_me() # fetches all users with a lower sortkey and returns it in a df       
    if df is None:
        st.warning("Missing context: 'role_sortkey' not in session_state.")
    elif df.empty:
        st.info("No user with a lower sortkey found.")
    else:
        st.dataframe(df, width="stretch")

with right:
    st.subheader("User Management")
    register_user_dropdown_admin()
    del_user_dropdown_admin()
    edit_user_dropdown_admin(title="Edit user")
