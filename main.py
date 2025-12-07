"""main.py is the login page which should be called locally in order to run the app. It contains the login structure and
redirects the app user to the different pages according to their role/ sortkey. The necessary functions are imported from
db_functions_users.py."""

import streamlit as st
import time
from db.db_functions_users import create_tables, add_user, get_user_by_credentials, get_role_sortkey, register_main, get_user_ID, get_manager_ID, initialize_data, add_user
import pandas as pd
import requests
from sqlalchemy import create_engine

# The engine serves as a central gateway to the database (MS Azure SQL). 
# It manages the connections and translates Python commands into the appropriate SQL dialect.
# pandas requires this!
DATABASE_URI = st.secrets["azure_db"]["ENGINE"]
engine = create_engine(DATABASE_URI)

# admin password from st.secrets
ADMIN = st.secrets["dummy"]["ADMIN"]

# basic page settings
st.set_page_config(page_title="Login", layout="centered", initial_sidebar_state="collapsed")
st.title("Login")

ADMIN = st.secrets["dummy"]["ADMIN"]

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
# add ADMIN to user.db if they do not exist
def create_first_users():
    ckeck_users_df = pd.read_sql_query("""
        SELECT username FROM users 
        WHERE username = ? OR username = ? OR username = ?
        """, engine, params=('Admin', 'Manager', 'User')
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
        st.success(f"Welcome {uname}! Role: {role}")
        time.sleep(1)
        if role == "Administrator":
            st.switch_page("pages/admin_overview.py")
        elif role == "Manager":
            st.switch_page("pages/manager_overview.py")
        else:
            st.switch_page("pages/user_overview.py")
    else:
        st.error("Wrong username or password.")

# ---- Text unterhalb des Login-Forms anzeigen ----
st.markdown(
    """
    ---
    Not registered yet? You can register as a manager and start planning your business-trips within your company, create a new account and start inviting your employees. Register now:
    """
)

register_main()
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
#        elif role == "Manager":
#        st.success(f"Welcome {uname}! Role: {role}")
#        time.sleep(1)
#        if role == "Administrator":
#            st.switch_page("pages/admin_overview.py")
#            st.switch_page("pages/manager_overview.py")
#        else:
#            st.switch_page("pages/user_overview.py")
#    else:
#        st.error("Wrong username or password.")

#" "
#" "
#" "
#" "
#"""
#Not registered yet? You can register as a manager and start planning your business-trips within your company, create a new account and start inviting your employees. Register now:"""
#register_main()
