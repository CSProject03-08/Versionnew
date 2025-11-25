import streamlit as st
import pandas as pd
import sqlite3
from db.db_functions_users import register_user_dropdown_admin, del_user_dropdown, edit_user_dropdown_admin, get_users_under_me, del_user_dropdown_admin
st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("Admin Dashboard")

### Access control, so only admin can access this page ###
if "role" not in st.session_state or st.session_state["role"] != "Administrator":
    st.error("Access denied. Please log in as Administrator.")
    st.stop()


left, right = st.columns([4, 2], gap="large")
with left:
    st.subheader("Table")
    df = get_users_under_me()         
    if df is None:
        st.warning("Fehlender Kontext: 'role_sortkey' ist nicht im session_state.")
    elif df.empty:
        st.info("Keine Benutzer unter deiner Rolle.")
    else:
        st.dataframe(df, use_container_width=True)

with right:
    st.subheader("User Management")
    register_user_dropdown_admin()
    del_user_dropdown_admin()
    edit_user_dropdown_admin(title="Edit user")