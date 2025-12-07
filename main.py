"""main.py is the login page which should be called locally in order to run the app. It contains the login structure and
redirects the app user to the different pages according to their role/ sortkey. The necessary functions are imported from
db_functions_users.py."""

import streamlit as st
import time
from db.db_functions_users import create_tables, add_user, get_user_by_credentials, get_role_sortkey, register_main, get_user_ID, get_manager_ID, initialize_data, add_user
import pandas as pd
import requests
import pyodbc

#basic page settings
st.set_page_config(page_title="Login", layout="centered", initial_sidebar_state="collapsed")
st.title("Login")

### pulling crucial access infromation from streamlit secrets file ###
SERVER_NAME = st.secrets["azure_db"]["SERVER_NAME"]
DATABASE_NAME = st.secrets["azure_db"]["DATABASE_NAME"]
USERNAME = st.secrets["azure_db"]["USERNAME"]
PASSWORD = st.secrets["azure_db"]["PASSWORD"]

### creating connection object referring to the MS Azure database ###
CONNECTION_STRING = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    f'SERVER={SERVER_NAME};'
    f'DATABASE={DATABASE_NAME};'
    f'UID={USERNAME};'
    f'PWD={PASSWORD};'
    'Encrypt=yes;'  
    'TrustServerCertificate=no;'
)


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
    except pyodbc.Error as ex: # raises error in case the connection is not possible
        sqlstate = ex.args[0]
        st.error(f"Connection error: {sqlstate}")
        return None

# display of the current ip adress from streamlit to adjust the firewall of MS Azure when app gets rebooted
def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        return response.json()['ip']
    except Exception as e:
        return f"Error: {e}"

st.write(f"The public IP address of the streamlit app is: **{get_public_ip()}**")

#create db and table 'users' if non-existent
create_tables()
initialize_data()
# add dummies to user.db if they do not exist
def create_first_users():
    conn = connect()
    ckeck_users_df = pd.read_sql_query("""
        SELECT username FROM users 
        WHERE username = 'Admin' OR 'Manager' OR 'User' 
        """, conn
    )

    if len(ckeck_users_df) == 0:
        add_user("Admin", "123", "a@gmail.com", "Administrator")
        add_user("Manager", "123", "manager@gmail.com", "Manager")
        add_user("User", "123", "user@gmail.com", "User")

    else:
        pass
    
create_first_users()

# Login-inputs, with censored password
with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")


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

" "
" "
" "
" "
"""
Not registered yet? You can register as a manager and start planning your business-trips within your company, create a new account and start inviting your employees. Register now:"""
register_main()
