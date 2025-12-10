"""main.py is the login page which should be called locally in order to run the app. It contains the login structure and
redirects the app user to the different pages according to their role/ sortkey. The necessary functions are imported from
db_functions_users.py."""

import streamlit as st
import time
import pyodbc
from db.db_functions_users import create_tables, add_user, get_user_by_credentials, get_role_sortkey, register_main, get_user_ID, get_manager_ID, initialize_data, add_user
import pandas as pd
import requests
from sqlalchemy import create_engine
import urllib
from utils import hide_sidebar, load_secrets

# basic page settings
st.set_page_config(page_title="Login", layout="centered", initial_sidebar_state="collapsed")
hide_sidebar()
st.title("Login")

CONNECTION_STRING = load_secrets()

# admin password from st.secrets
ADMIN = st.secrets["dummy"]["ADMIN"]

#create db and table 'users' if non-existent
create_tables()

# create table 'roles' and initialize data if non-existent
initialize_data()

def create_first_users():
    """"This function creates the first admin if no admin exists yet in the users table.
    
    Args:
        None
        
    Returns:
        None"""
    
    # create engine and connection   
    connect_uri = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(CONNECTION_STRING)
    engine = create_engine(connect_uri, fast_executemany=True)

    ckeck_users_df = pd.read_sql_query("""
        SELECT username FROM users 
        WHERE username = ?
        """, engine, params=('Admin',)
    )

    if len(ckeck_users_df) == 0:
        add_user("Admin", ADMIN, "a@gmail.com", "Administrator")
    else:
        pass

# call the function to create the first admin if not existent
create_first_users()

# Login-inputs, with censored password
with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

if submitted:
    result = get_user_by_credentials(username, password) # returns (username, role) if credentials are correct, else None
    if result:
        uname, role = result
        # Set session state variables
        st.session_state["username"] = uname
        st.session_state["role"] = role
        role_sortkey = get_role_sortkey(role)
        st.session_state["role_sortkey"] = role_sortkey
        st.session_state["user_ID"] = get_user_ID(uname)
        st.session_state["manager_ID"] = get_manager_ID(uname)
        st.success(f"Welcome {uname}! Role: {role}")
        time.sleep(1)
        # Redirect based on role
        if role == "Administrator":
            st.switch_page("pages/admin_overview.py")
        elif role == "Manager":
            st.switch_page("pages/manager_overview.py")
        else:
            st.switch_page("pages/user_overview.py")
    # If credentials are incorrect raise error message
    else:
        st.error("Wrong username or password.")

# Registration for new managers
"""Not registered yet? You can register as a manager and start planning your business-trips within your company, create a new account and start inviting your employees. Register now:"""
register_main()
