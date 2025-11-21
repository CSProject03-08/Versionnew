import sqlite3
import time
import streamlit as st
import pandas as pd
DB_USERS = "db/users.db"

### Connecting to the database users.db ###
def connect():
    return sqlite3.connect(DB_USERS)

### Creating necessary tables for different role in main.py ###
def create_tables():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT NOT NULL,
        email TEXT,
        role TEXT NOT NULL,
        manager_ID INTEGER,
        FOREIGN KEY (role) REFERENCES roles (role)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role TEXT PRIMARY KEY,
        sortkey INTEGER NOT NULL
    )
    """)

    c.executemany("""
    INSERT OR IGNORE INTO roles (role, sortkey)
    VALUES (?, ?)
    """, [
        ("Administrator", 3),
        ("Manager", 2),
        ("User", 1)
    ])

    conn.commit()
    conn.close()

### we use user_ID of the manager, to add their user_ID to the users they create with another column manager_id, so manager only have access to these users, they've created ###
def get_user_ID(username: str):
    conn = connect()
    c = conn.cursor()

    c.execute("SELECT user_ID FROM users WHERE username = ?", (username,))
    row = c.fetchone()

    conn.close()

    if row:
        return row[0]
    return None

def get_manager_ID(username: str):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT manager_ID FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

### Adding users ###
def add_user(username, password, email, role):
    conn = connect()
    c = conn.cursor()
    manager_ID = st.session_state.get("user_ID", None)
    try:
        c.execute(
            "INSERT INTO users (username, password, email, role, manager_ID) VALUES (?, ?, ?, ?, ?)",
            (username, password, email, role, manager_ID)
        )
        conn.commit()
        print(f"✅ User '{username}' sucessfully added!")
    except sqlite3.IntegrityError:
        print(f"User '{username}' exists already.")
    finally:
        conn.close()

### Comparison from inputs to databank ###
def get_user_by_credentials(username, password):
    conn = connect()
    c = conn.cursor()
    c.execute(
        "SELECT username, role FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    user = c.fetchone()
    conn.close()
    return user

### Assign sortkey to roles for user management ###
def get_role_sortkey(role):
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()
    c.execute('SELECT sortkey FROM roles WHERE role = ?', (role,))
    data = c.fetchone()[0]
    conn.close()
    return data

### List of all users under own role_sortkey ###
def list_roles_editable():
    current_sortkey = st.session_state["role_sortkey"]
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()

    c.execute("""
        SELECT role, sortkey
        FROM roles
        WHERE sortkey < ?
        ORDER BY sortkey DESC
    """, (current_sortkey,))

    roles = c.fetchall()
    conn.close()
    return roles

### returns all users which the manager has created ###
def get_users_for_current_manager():
    if "user_ID" not in st.session_state:
        return []

    manager_id = st.session_state["user_ID"]

    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT user_ID, username, email, role
        FROM users
        WHERE manager_ID = ?
        ORDER BY username
    """, (manager_id,))
    rows = c.fetchall()
    conn.close()
    return rows

### Dropdown for manager page to register someone ###
def register_user_dropdown(title: str = "Register new user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to add new users")
        return

    roles = list_roles_editable()
    role_names = [r[0] for r in roles]

    with st.expander(title, expanded=False):
        with st.form("register_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Username")
                email    = st.text_input("E-mail")
            with col2:
                password  = st.text_input("Password", type="password")
                password2 = st.text_input("Confirm password", type="password")
                role      = st.selectbox("Rolle", role_names if role_names else ["— no available role —"])

            submitted = st.form_submit_button("Register")

        if submitted:
            if not username or not password:
                st.warning("Please enter username and password")
                return
            if password != password2:
                st.error("Passwords aren't identical")
                return
            if not role_names or role not in role_names:
                st.error("You're not allowed to add this role")
                return

            try:
                add_user(username, password, email, role)
                st.success(f"User **{username}** was registered")
                time.sleep(2)
                st.rerun()
            except sqlite3.IntegrityError as e:
                st.error(f"Registration failed (maybe already exists): {e}")
            except Exception as e:
                st.error(f"Unexpected Error: {e}")

### Dropdown for admin page to register someone ###
def register_user_dropdown_admin(title: str = "Register new user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to add new users")
        return

    roles = list_roles_editable()
    role_names = [r[0] for r in roles]

    with st.expander(title, expanded=False):
        with st.form("register_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Username")
                email    = st.text_input("E-mail")
                manager_ID = st.text_input("Manager ID")
            with col2:
                password  = st.text_input("Password", type="password")
                password2 = st.text_input("Confirm password", type="password")
                role      = st.selectbox("Rolle", role_names if role_names else ["— no available role —"])

            submitted = st.form_submit_button("Register")

        if submitted:
            if not username or not password:
                st.warning("Please enter username and password")
                return
            if password != password2:
                st.error("Passwords aren't identical")
                return
            if not role_names or role not in role_names:
                st.error("You're not allowed to add this role")
                return

            try:
                add_user(username, password, email, role)
                st.success(f"User **{username}** was registered")
                time.sleep(2)
                st.rerun()
            except sqlite3.IntegrityError as e:
                st.error(f"Registration failed (maybe already exists): {e}")
            except Exception as e:
                st.error(f"Unexpected Error: {e}")


### Dropdown for manager page to delete someone ###
def del_user_dropdown(title: str = "Delete user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to delete users.")
        return

    current_sortkey = st.session_state["role_sortkey"]
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()

    c.execute("""
        SELECT u.username, u.role
        FROM users u
        JOIN roles r ON u.role = r.role
        WHERE r.sortkey < ? 
        AND u.manager_ID = ?
        ORDER BY r.sortkey DESC
    """, (current_sortkey, st.session_state["user_ID"]))
    users = c.fetchall()
    conn.close()

    if not users:
        st.info("No deletable users available.")
        return

    with st.expander(title, expanded=False):
        user_list = [f"{u[0]}  ·  {u[1]}" for u in users]
        selected_user = st.selectbox("Select user to delete", user_list)

        if st.button("Delete user"):
            username = selected_user.split("·")[0].strip()
            conn = sqlite3.connect(DB_USERS)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            st.success(f"✅ User '{username}' has been deleted.")
            time.sleep(2)
            st.rerun()

### Dropdown for Admin page to delete someone ###
def del_user_dropdown_admin(title: str = "Delete user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to delete users.")
        return

    current_sortkey = st.session_state["role_sortkey"]
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()

    c.execute("""
        SELECT u.username, u.role
        FROM users u
        JOIN roles r ON u.role = r.role
        WHERE r.sortkey < ? 
        ORDER BY r.sortkey DESC
    """, (current_sortkey,))
    users = c.fetchall()
    conn.close()

    if not users:
        st.info("No deletable users available.")
        return

    with st.expander(title, expanded=False):
        user_list = [f"{u[0]}  ·  {u[1]}" for u in users]
        selected_user = st.selectbox("Select user to delete", user_list)

        if st.button("Delete user"):
            username = selected_user.split("·")[0].strip()
            conn = sqlite3.connect(DB_USERS)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            st.success(f"✅ User '{username}' has been deleted.")
            time.sleep(2)
            st.rerun()

### Dropdown for manager page to edit existing person ###
def edit_user_dropdown(title: str = "Edit user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to edit users.")
        return

    current_sortkey = st.session_state["role_sortkey"]

    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()

    c.execute("""
        SELECT u.username, u.email, u.password, u.role
        FROM users u
        JOIN roles r ON u.role = r.role
        WHERE r.sortkey < ? 
        AND u.manager_ID = ?
        ORDER BY r.sortkey DESC
    """, (current_sortkey, st.session_state["user_ID"]))
    users = c.fetchall()
    conn.close()

    if not users:
        st.info("No editable users available.")
        return

    with st.expander(title, expanded=False):
        user_list = [u[0] for u in users]
        selected_user = st.selectbox("Select user to edit", user_list)

        conn = sqlite3.connect(DB_USERS)
        c = conn.cursor()
        c.execute("SELECT username, password, email, role FROM users WHERE username = ?", (selected_user,))
        user_data = c.fetchone()
        conn.close()

        if not user_data:
            st.warning("User not found.")
            return

        username, password, email, role = user_data

        with st.form("edit_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username", value=username)
                new_email = st.text_input("E-Mail", value=email)
            with col2:
                new_password = st.text_input("Password", value=password, type="password")
                new_role = st.text_input("Role", value=role)  

            submitted = st.form_submit_button("Save changes")

        if submitted:
            conn = sqlite3.connect(DB_USERS)
            c = conn.cursor()
            c.execute("""
                UPDATE users
                SET username = ?, password = ?, email = ?, role = ?
                WHERE username = ?
            """, (new_username, new_password, new_email, new_role, username))
            conn.commit()
            conn.close()

            st.success(f"✅ User '{username}' updated successfully.")
            time.sleep (2)
            st.rerun()

### Dropdown for Admin page to edit existing person ###
def edit_user_dropdown_admin(title: str = "Edit user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to edit users.")
        return

    current_sortkey = st.session_state["role_sortkey"]

    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()

    c.execute("""
        SELECT u.username, u.email, u.password, u.role, u.manager_ID
        FROM users u
        JOIN roles r ON u.role = r.role
        WHERE r.sortkey < ?
        ORDER BY r.sortkey DESC
    """, (current_sortkey,))
    users = c.fetchall()
    conn.close()

    if not users:
        st.info("No editable users available.")
        return

    with st.expander(title, expanded=False):
        user_list = [u[0] for u in users]
        selected_user = st.selectbox("Select user to edit", user_list)

        conn = sqlite3.connect(DB_USERS)
        c = conn.cursor()

        c.execute("""
            SELECT username, password, email, role, manager_ID
            FROM users
            WHERE username = ?
        """, (selected_user,))
        user_data = c.fetchone()
        conn.close()

        if not user_data:
            st.warning("User not found.")
            return

        username, password, email, role, manager_ID = user_data

        with st.form("edit_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username   = st.text_input("Username", value=username)
                new_email      = st.text_input("E-Mail", value=email)
                new_manager_ID = st.text_input("Manager ID", value=str(manager_ID))
            with col2:
                new_password = st.text_input("Password", value=password, type="password")
                new_role     = st.text_input("Role", value=role)

            submitted = st.form_submit_button("Save changes")

        if submitted:
            conn = sqlite3.connect(DB_USERS)
            c = conn.cursor()

            c.execute("""
                UPDATE users
                SET username = ?, password = ?, email = ?, role = ?, manager_ID = ?
                WHERE username = ?
            """, (
                new_username, new_password, new_email,
                new_role, new_manager_ID, username
            ))

            conn.commit()
            conn.close()

            st.success(f"✅ User '{username}' updated successfully.")
            time.sleep(1.5)
            st.rerun()

### Dropdown for main page to register as manager ###
def register_main(title: str = "Register as manager"):
    with st.expander(title, expanded=False):
        with st.form("register_main_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("Username")
                email = st.text_input("E-mail")
            with col2:
                password = st.text_input("Password", type="password")
                password2 = st.text_input("Confirm Password", type="password")

            submitted = st.form_submit_button("Register")

        if submitted:
            if not username or not password:
                st.warning("Please enter username and password.")
                return
            if password != password2:
                st.error("Passwords aren't identical.")
                return

            role = "Manager"

            try:
                conn = sqlite3.connect(DB_USERS)
                c = conn.cursor()

                c.execute(
                    "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                    (username, password, email, role)
                )
                conn.commit()

                c.execute("SELECT user_ID FROM users WHERE username = ?", (username,))
                new_user_id = c.fetchone()[0]

                c.execute(
                    "UPDATE users SET manager_ID = ? WHERE user_ID = ?",
                    (new_user_id, new_user_id)
                )
                conn.commit()

                conn.close()

                st.success(f"✅ Manager '{username}' was successfully added. You can now log in.")
                time.sleep(2)
                st.rerun()

            except sqlite3.IntegrityError:
                st.error("⚠️ Manager already exists.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

### Input window to change user data in users.db ###
def edit_own_profile(title: str = "My profile"):
    if "username" not in st.session_state:
        st.warning("Log in first.")
        return

    current_user = st.session_state["username"]

    conn = connect()
    c = conn.cursor()
    c.execute("SELECT username, email, password, role FROM users WHERE username = ?", (current_user,))
    row = c.fetchone()
    if not row:
        conn.close()
        st.error("User not found.")
        return

    username, email, stored_pw, role = row

    st.subheader(title)
    st.caption(f"Role: **{role}** (is not editable)")

    with st.form("edit_self_form"):
        new_username = st.text_input("Username", value=username, disabled = True)
        new_email    = st.text_input("E-Mail", value=email or "")

        st.markdown("**Passwort ändern (optional)**")
        pw1 = st.text_input("Neues Passwort", type="password", placeholder="Leer lassen, um altes zu behalten")
        pw2 = st.text_input("Neues Passwort bestätigen", type="password")

        submitted = st.form_submit_button("Safe changes")

    if not submitted:
        conn.close()
        return

    if pw1 or pw2:
        if pw1 != pw2:
            conn.close()
            st.error("Passwörter stimmen nicht überein.")
            return
        new_password = pw1
    else:
        new_password = stored_pw 

    try:
        c.execute("""
            UPDATE users
               SET username = ?, email = ?, password = ?
             WHERE username = ?
        """, (new_username, new_email, new_password, username))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        st.error("User exists already.")
        return
    finally:
        conn.close()

    if new_username != username:
        st.session_state["username"] = new_username

    st.success("Profile has been updated")
    st.rerun()

### Creates table for admin dashboard to see all registered managers/users ###
def get_users_under_me() -> pd.DataFrame | None:
    if "role_sortkey" not in st.session_state:
        return None

    current = st.session_state["role_sortkey"]
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()
    c.execute("""
        SELECT u.username, u.email, u.role, r.sortkey, u.manager_ID
        FROM users u
        JOIN roles r ON u.role = r.role
        WHERE r.sortkey < ?
        ORDER BY r.sortkey DESC, u.username
    """, (current,))
    rows = c.fetchall()
    conn.close()

    return pd.DataFrame(rows, columns=["username", "email", "role", "sortkey", "manager_ID"])