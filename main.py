import streamlit as st
import time
from db.db_functions_users import create_tables, add_user, get_user_by_credentials, get_role_sortkey, register_main, get_user_ID, get_manager_ID
import bcrypt

### basic page settings ###
st.set_page_config(page_title="Login", layout="centered", initial_sidebar_state="collapsed")
st.title("Login")

### create db and table if non-existent ###
create_tables()
### add dummies to user.db ###
password = "123"
hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
add_user("Admin", hashed_pw, "a@gmail.com", "Administrator")
add_user("Manager", hashed_pw, "manager@gmail.com", "Manager")
add_user("User", hashed_pw, "user@gmail.com", "User")

### Login-inputs, with censored password ###
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
