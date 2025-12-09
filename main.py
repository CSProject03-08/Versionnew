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
from utils import hide_sidebar

# The engine serves as a central gateway to the database (MS Azure SQL). 
# It manages the connections and translates Python commands into the appropriate SQL dialect.
# pandas requires this!
DATABASE_URI = st.secrets["azure_db"]["ENGINE"]
engine = create_engine(DATABASE_URI)

# Fetching for all information in the st.secrets and defining the connection string for the normal connection where pandas is not involved
SERVER_NAME = st.secrets["azure_db"]["SERVER_NAME"]
DATABASE_NAME = st.secrets["azure_db"]["DATABASE_NAME"]
USERNAME = st.secrets["azure_db"]["USERNAME"]
PASSWORD = st.secrets["azure_db"]["PASSWORD"]

CONNECTION_STRING = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    f'SERVER={SERVER_NAME};'
    f'DATABASE={DATABASE_NAME};'
    f'UID={USERNAME};'
    f'PWD={PASSWORD};'
    'Encrypt=yes;'  
    'TrustServerCertificate=no;'
)

# admin password from st.secrets
ADMIN = st.secrets["dummy"]["ADMIN"]

# basic page settings
st.set_page_config(page_title="Login", layout="centered", initial_sidebar_state="collapsed")
hide_sidebar()
st.title("Login")

ADMIN = st.secrets["dummy"]["ADMIN"]

# display of the current ip adress from streamlit to adjust the firewall of MS Azure when app gets rebooted
#def get_public_ip():
#    try:
#        response = requests.get('https://api.ipify.org?format=json')
#        return response.json()['ip']
#    except Exception as e:
#        return f"Error: {e}"

#st.write(f"The public IP address of the streamlit app is: **{get_public_ip()}**")

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
        st.error(f"Connection error: {sqlstate}")
        return None

def get_public_ip() -> str:
    """
    Tries to fetch the public IP. Never raises,
    always returns a string (either IP or error message).
    """
    try:
        resp = requests.get("https://api.ipify.org?format=json", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("ip", "unknown")
    except Exception as e:
        # Alles abfangen und nur als Text zurückgeben
        return f"Error fetching IP: {e}"

ip_info = get_public_ip()
st.caption(f"The public IP address of the streamlit app is: **{ip_info}**")


#create db and table 'users' if non-existent
create_tables()
initialize_data()
# add ADMIN to user.db if they do not exist
def create_first_users():
    ckeck_users_df = pd.read_sql_query("""
        SELECT username FROM users 
        WHERE username = ? OR username = ? OR username = ?
        """, conn, params=('Admin', 'Manager', 'User')
    )

    if len(ckeck_users_df) == 0:
        add_user("Admin", ADMIN, "a@gmail.com", "Administrator")
    else:
        pass
    
create_first_users()

# Login-inputs, with censored password
with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

# ... alles oben bleibt wie es ist ...

#if submitted:
#    result = get_user_by_credentials(username, password)
#    if result:
#        uname, role = result
#        st.session_state["username"] = uname
#        st.session_state["role"] = role
#        role_sortkey = get_role_sortkey(role)
#        st.session_state["role_sortkey"] = role_sortkey
#        st.session_state["user_ID"] = get_user_ID(uname)
#        st.session_state["manager_ID"] = get_manager_ID(uname)
#    elif role == "Manager":
#        st.success(f"Welcome {uname}! Role: {role}")
#        time.sleep(1)
#        if role == "Administrator":
#            st.switch_page("pages/admin_overview.py")
#            st.switch_page("pages/manager_overview.py")
#        else:
#            st.switch_page("pages/user_overview.py")
#    else:
#        st.error("Wrong username or password.")
#
#" "
#" "
#" "
#" "
#"""
#Not registered yet? You can register as a manager and start planning your business-trips within your company, create a new account and start inviting your employees. Register now:"""
#register_main()

if submitted:
    result = get_user_by_credentials(username, password)
    if result:
        uname, role = result
        st.session_state["username"] = uname
        st.session_state["role"] = role
        role_sortkey = get_role_sortkey(role)
        st.session_state["role_sortkey"] = role_sortkey
        st.session_state["user_ID"] = get_user_ID(uname)
        st.session_state["manager_ID"] = get_manager_ID(uname)
        st.success(f"Welcome {uname}! 🎉 Role: {role}")
        time.sleep(1)
        if role == "Administrator":
            st.switch_page("pages/admin_overview.py")
        elif role == "Manager":
            st.switch_page("pages/manager_overview.py")
        else:
            st.switch_page("pages/user_overview.py")
    else:
        st.error("Wrong username or password.")



#"""Not registered yet? You can register as a manager and start planning your business-trips within your company, create a new account and start inviting your employees. Register now:"""
register_main()
