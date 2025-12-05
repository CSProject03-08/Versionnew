import pyodbc
import time
import streamlit as st
import pandas as pd
import bcrypt

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

def connect():
    """Connects to Azure SQL-database"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # show the error
        st.error(f"Connection error: {sqlstate}")
        return None

def create_tables():
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    # --- 1. ROLES-Tabelle erstellen (Muss VOR users erstellt werden) ---
    try:
        c.execute("""
        IF OBJECT_ID('roles', 'U') IS NULL 
        BEGIN
            CREATE TABLE roles (
                role VARCHAR(50) PRIMARY KEY,
                sortkey INT NOT NULL
            )
        END
        """)
        print("Tabelle 'roles' erstellt oder existiert bereits.")
    except pyodbc.Error as e:
        # Hier könnten wir prüfen, ob der Fehler ein existierendes Objekt ist
        print(f"Fehler beim Erstellen von 'roles': {e}")
        pass


    # --- 2. USERS-Tabelle erstellen ---
    try:
        # IDENTITY(1,1) ist die korrekte Syntax für AUTOINCREMENT in Azure SQL
        c.execute("""
        IF OBJECT_ID('users', 'U') IS NULL
        BEGIN
            CREATE TABLE users (
                user_ID INT PRIMARY KEY IDENTITY(1,1),
                username VARCHAR(255) UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                role VARCHAR(50) NOT NULL,
                manager_ID INT,
                FOREIGN KEY (role) REFERENCES roles (role)
            )
        END
        """)
        print("Tabelle 'users' erstellt oder existiert bereits.")
    except pyodbc.Error as e:
        print(f"Fehler beim Erstellen von 'users': {e}")
        pass

    conn.commit()
    conn.close()


def initialize_data():
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    # --- 1. Rollen bedingt einfügen ---
    roles_to_insert = [
        ("Administrator", 3),
        ("Manager", 2),
        ("User", 1)
    ]
    
    for role_name, sortkey_val in roles_to_insert:
        # Korrekte T-SQL Logik: Prüft, ob der Wert existiert, und fügt ihn nur dann ein
        try:
            c.execute("""
                IF NOT EXISTS (SELECT 1 FROM roles WHERE role = ?)
                BEGIN
                    INSERT INTO roles (role, sortkey) VALUES (?, ?)
                END
            """, role_name, role_name, sortkey_val)
        except pyodbc.Error as e:
            # Wird nur ausgeführt, wenn etwas anderes als eine Duplizierung fehlschlägt
            print(f"Fehler beim Einfügen der Rolle {role_name}: {e}")
            pass
            
    # --- 2. Admin-User bedingt einfügen ---
    # Fügen Sie den Admin nur ein, wenn er noch nicht existiert
    #admin_username = 'Admin'
    #admin_password = '123'
    #admin_email = "admin@hsg.ch"
    #admin_role = 'Administrator'
    
    #try:
        #c.execute("""
            #IF NOT EXISTS (SELECT 1 FROM users WHERE username = ?)
            #BEGIN
                #INSERT INTO users (username, password, email, role, manager_ID)
                #VALUES (?, ?, ?, ?, ?)
            #END
        #""", admin_username, admin_username, admin_password, admin_email, admin_role, None)
    #except pyodbc.Error as e:
        #print(f"Fehler beim Einfügen des Admin-Users: {e}")
        #pass
            
    conn.commit()
    conn.close()

def get_user(username):
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data


### we use user_ID of the manager, to add their user_ID to the users they create with another column manager_id, so manager only have access to the users, they've created ###
def get_user_ID(username: str):
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    c.execute("SELECT user_ID FROM users WHERE username = ?", (username,))
    row = c.fetchone()

    conn.close()

    if row:
        return row[0]
    return None

def get_manager_ID(username: str):
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute("SELECT manager_ID FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

### Adding users ###
def add_user(username, password, email, role):
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    manager_ID = st.session_state.get("user_ID", None)
    try:
        c.execute(
            "INSERT INTO users (username, password, email, role, manager_ID) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_pw, email, role, manager_ID)
        )
        conn.commit()
        print(f"✅ User '{username}' sucessfully added!")
    except pyodbc.Error as ex:
        print(f"User '{username}' exists already or another database error occurred: {ex}")
    finally:
        conn.close()

### Comparison from inputs to databank, old is without bcyrypt as backup here ###
def get_user_by_credentials_old(username, password):
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute(
        "SELECT username, role FROM users WHERE username = ? AND password = ?",
        (username, hashed_pw)
    )
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_credentials(username, password):
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute(
        "SELECT username, password, role FROM users WHERE username = ?",
        (username,)
    )
    row = c.fetchone()
    conn.close()

    if row is None:
        return None

    stored_username, stored_hash, stored_role = row

    # safety check: ensure stored_hash is bytes
    if isinstance(stored_hash, str):
        try:
            stored_hash = stored_hash.encode("utf-8")
        except Exception:
            return None
    if stored_hash is None:
        return None

    if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return (stored_username, stored_role)
    else:
        return None

### Assign sortkey to roles for user management ###
def get_role_sortkey(role):
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute('SELECT sortkey FROM roles WHERE role = ?', (role,))
    row = c.fetchone()[0]
    conn.close()
    if row:
        return row
    return None

### List of all users under own role_sortkey ###
def list_roles_editable():
    current_sortkey = st.session_state["role_sortkey"]
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    c.execute("""
        SELECT role, sortkey
        FROM roles
        WHERE sortkey < ?
        ORDER BY sortkey DESC
    """, (current_sortkey,))

    roles = c.fetchall()
    conn.close()
    if roles:
        return roles
    return []

### returns all users which the manager has created ###
def get_users_for_current_manager():
    if "user_ID" not in st.session_state:
        return []

    manager_id = st.session_state["user_ID"]

    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute("""
        SELECT user_ID, username, email, role
        FROM users
        WHERE manager_ID = ?
        ORDER BY username
    """, (manager_id,))
    rows = c.fetchall()
    conn.close()
    if rows:
        return rows
    return []

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
            except pyodbc.Error as e:
                st.error(f"Registration failed due to a database error: {e}")
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
            except pyodbc.Error as e:
                st.error(f"Registration failed due to a database error: {e}")
            except Exception as e:
                st.error(f"Unexpected Error: {e}")


### Dropdown for manager page to delete someone ###
def del_user_dropdown(title: str = "Delete user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to delete users.")
        return

    current_sortkey = st.session_state["role_sortkey"]
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    manager_id = st.session_state["user_ID"]

    c.execute("""
        SELECT u.username, u.role
        FROM users u
        JOIN roles r ON u.role = r.role
        WHERE r.sortkey < ? 
        AND u.manager_ID = ?
        ORDER BY r.sortkey DESC
    """, (current_sortkey, manager_id))
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
            conn = connect()
            if conn is None:
                return
            c = conn.cursor()
            try:
                c.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                st.success(f"✅ User '{username}' has been deleted.")
                time.sleep(2)
                st.rerun()
            
            # error if this is a manager that is assigned to other users
            except pyodbc.Error as e:
                st.error(f"Deletion failed due to a database error: {e}")
            except Exception as e:
                st.error(f"Unexpected Error during deletion: {e}")
            finally:
                conn.close()

### Dropdown for Admin page to delete someone ###
def del_user_dropdown_admin(title: str = "Delete user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to delete users.")
        return

    current_sortkey = st.session_state["role_sortkey"]
    conn = connect()
    if conn is None:
        return
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
            conn = connect()
            if conn is None:
                return
            c = conn.cursor()
            try:
                c.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                conn.close()
                st.success(f"✅ User '{username}' has been deleted.")
                time.sleep(2)
                st.rerun()
            # error if this is a manager that is assigned to other users
            except pyodbc.Error as e:
                st.error(f"Deletion failed due to a database error: {e}")
            except Exception as e:
                st.error(f"Unexpected Error during deletion: {e}")
            finally:
                conn.close()

### Dropdown for manager page to edit existing person ###
def edit_user_dropdown(title: str = "Edit user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to edit users.")
        return

    current_sortkey = st.session_state["role_sortkey"]
    manager_id = st.session_state["user_ID"]

    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    c.execute("""
        SELECT u.username, u.email, u.password, u.role
        FROM users u
        JOIN roles r ON u.role = r.role
        WHERE r.sortkey < ? 
        AND u.manager_ID = ?
        ORDER BY r.sortkey DESC
    """, (current_sortkey, manager_id))
    users = c.fetchall()
    conn.close()

    if not users:
        st.info("No editable users available.")
        return

    with st.expander(title, expanded=False):
        user_list = [u[0] for u in users]
        selected_user = st.selectbox("Select user to edit", user_list, key="edit_user_select")
        selected_user_data = next((u for u in users if u[0] == selected_user), None) #should five queried datapoints back

        conn = connect()
        if conn is None:
            return
        c = conn.cursor()
        c.execute("SELECT username, password, email, role FROM users WHERE username = ?", (selected_user,))
        user_data = c.fetchone()
        conn.close()

        if not user_data:
            st.warning("User not found.")
            return

        username, current_email, current_password, current_role = selected_user_data

        editable_roles = list_roles_editable()
        editable_role_names = [r[0] for r in editable_roles]
        # Index der aktuell zugewiesenen Rolle in der Liste der bearbeitbaren Rollen
        try:
            default_role_index = editable_role_names.index(current_role)
        except ValueError:
            # Fallback, falls die aktuelle Rolle (was unwahrscheinlich ist) nicht in der editierbaren Liste ist
            default_role_index = 0

        with st.form("edit_user_form"):
            st.markdown(f"**Editing user: {username}**")
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username", value=username, key="edit_username")
                new_email = st.text_input("E-Mail", value=current_email if current_email else "", key="edit_email")
            with col2:
                new_password = st.text_input("New Password (Leave empty to keep current)", type="password", key="edit_password")
                new_role = st.selectbox(
                    "Role", 
                    editable_role_names, 
                    index=default_role_index,
                    key="edit_role"
                )   

            submitted = st.form_submit_button("Save changes")

            if submitted:
                # 1. Validierung
                if not new_username:
                    st.error("Username cannot be empty.")
                    return
                if new_role not in editable_role_names:
                    st.error("Invalid role selected.")
                    return

                # 2. Passwort-Update-Logik
                if new_password:
                    # Hash das neue Passwort
                    pw_to_store = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                else:
                    # Behalte den alten Hash bei
                    pw_to_store = current_password

                # 3. Datenbank-Update mit Fehlerbehandlung
                conn = connect()
                if conn is None:
                    return
                c = conn.cursor()
            
                try:
                    c.execute("""
                        UPDATE users
                        SET username = ?, password = ?, email = ?, role = ?
                        WHERE username = ?
                    """, (new_username, pw_to_store, new_email, new_role, username))
                
                    conn.commit()
                    st.success(f"✅ User '{username}' updated successfully.")
                    time.sleep (2)
                    st.rerun()
                
                except pyodbc.Error as e:
                    # Fängt Integritätsverletzungen (z.B. Duplizierter Username oder ungültige Rolle) ab
                    st.error(f"Update failed due to a database error: Check if the new username '{new_username}' already exists or if the role is valid. Details: {e}")
                except Exception as e:
                    st.error(f"Unexpected Error during update: {e}")
                finally:
                    conn.close()

                #hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                #conn = connect()
                #if conn is None:
                    #return
                #c = conn.cursor()
                #c.execute("""
                    #UPDATE users
                    #SET username = ?, password = ?, email = ?, role = ?
                    #WHERE username = ?
                #""", (new_username, hashed_pw, new_email, new_role, username))
                #conn.commit()
                #conn.close()

                #st.success(f"✅ User '{username}' updated successfully.")
                #time.sleep (2)
                #st.rerun()

### Dropdown for Admin page to edit existing person ###
def edit_user_dropdown_admin(title: str = "Edit user"):
    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to edit users.")
        return

    current_sortkey = st.session_state["role_sortkey"]

    conn = connect()
    if conn is None:
        return
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
        selected_user = st.selectbox("Select user to edit", user_list, index=None, key="admin_edit_user_select")
        selected_user_data = next((u for u in users if u[0] == selected_user), None) #should five queried datapoints back

        if not selected_user_data:
            st.warning("User not found yet.")
            return

        #c.execute("""
            #SELECT username, password, email, role, manager_ID
            #FROM users
            #WHERE username = ?
        #""", (selected_user,))
        #user_data = c.fetchone()
        #conn.close()

        username, current_email, current_password, current_role, current_manager_ID = selected_user_data
        editable_roles = list_roles_editable()
        editable_role_names = [r[0] for r in editable_roles]

        try:
            default_role_index = editable_role_names.index(current_role)
        except ValueError:
            default_role_index = 0

        with st.form("edit_user_form"):
            st.markdown(f"**Editing user: {username}**")
            col1, col2 = st.columns(2)
            with col1:
                new_username   = st.text_input("Username", value=username, key="admin_edit_username")
                new_email      = st.text_input("E-Mail", value=current_email, key="admin_edit_email")
                new_manager_ID = st.text_input("Manager ID", value=str(current_manager_ID), key="admin_edit_manager_ID")
            with col2:
                new_password = st.text_input("New Password (Leave empty to keep current)", type="password", key="admin_edit_password")
                new_role     = new_role = st.selectbox(
                    "Role", 
                    editable_role_names, 
                    index=default_role_index,
                    key="admin_edit_role"
                ) 

            submitted = st.form_submit_button("Save changes")

        if submitted:

            if not new_username:
                st.error("Username cannot be empty.")
                return
            if new_role not in editable_role_names:
                st.error("Invalid role selected.")
                return
            
            try:
                manager_id_int = int(new_manager_ID)
            except ValueError:
                st.error("Manager ID must be a valid integer.")
                return
            
            if new_password:
                # hash new password
                pw_to_store = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            else:
                # leave old password
                pw_to_store = current_password

            conn = connect()
            if conn is None:
                st.error("Update failed: Could not connect to database.")
                return
            c = conn.cursor()

            try:
                c.execute("""
                    UPDATE users
                    SET username = ?, password = ?, email = ?, role = ?, manager_ID = ?
                    WHERE username = ?
                """, (new_username, pw_to_store, new_email, new_role, manager_id_int, username))
                
                conn.commit()
                st.success(f" User '{username}' updated successfully.")
                time.sleep (2)
                st.rerun()

            except pyodbc.Error as e:
                # catches invalide entries (i.e. doubled username)
                st.error(f"Update failed due to a database error: Check if the new username '{new_username}' already exists, or if the role/manager_ID is valid. Details: {e}")
            except Exception as e:
                st.error(f"Unexpected Error during update: {e}")
            finally:
                conn.close()

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
                add_user(username, password, email, role) # catches duplication error already

                conn = connect()
                if conn is None:
                    st.error("Registration successful, but self-assignment failed: Could not connect to database.")
                    return
                c = conn.cursor()
                c.execute("SELECT user_ID FROM users WHERE username = ?", (username,))
                new_user_id = c.fetchone()
                
                if new_user_id:
                    new_user_id = new_user_id[0]
                    c.execute(
                        "UPDATE users SET manager_ID = ? WHERE user_ID = ?",
                        (new_user_id, new_user_id)
                    )
                    conn.commit()
                    st.success(f"Manager '{username}' was successfully added. You can now log in.")
                else:
                    st.warning("User created, but failed to retrieve user_ID for self-assignment.")

                time.sleep(2)
                st.rerun()

            except pyodbc.Error as e:
                # catches failure after add_user function
                st.error(f"A database error occurred during self-assignment (Manager ID update failed): {e}")
            except Exception as e:
                # catches every failure
                st.error(f"Unexpected error: {e}")
            finally:
                conn.close()

### Input window to change user data in users.db ###
def edit_own_profile(title: str = "My profile"):
    if "username" not in st.session_state or "user_ID" not in st.session_state:
        st.warning("Log in first.")
        return

    user_id = st.session_state["user_ID"]

    conn = connect()
    if not conn:
        st.error("Could not connect to database.")
        return
    
    try:
        c = conn.cursor()
        c.execute("SELECT username, email, password, role FROM users WHERE user_ID = ?", (user_id,))
        row = c.fetchone()

        if not row:
            st.error("User not found.")
            return

        original_username, original_email, stored_pw, original_role = row
        st.session_state["username"] = original_username #check weather session-state is at current

    except Exception as e:
        st.error(f"Error fetching user data: {e}")
        return
    finally:
        conn.close()
    
    st.subheader(title)
    st.caption(f"Role: **{original_role}** (is not editable)")

    with st.form("edit_self_form"):
        st.text_input("Username", value=original_username, disabled = True)
        #new_username = st.text_input("Username", value=username, disabled = True)
        new_email    = st.text_input("E-Mail", value=original_email or "")

        st.markdown("**Change password (optional)**")
        pw1 = st.text_input("New password", type="password", placeholder="leave empty to keep current password")
        pw2 = st.text_input("Confirm new password", type="password")

        submitted = st.form_submit_button("Safe changes")

    if submitted:

        if pw1 or pw2:
            if pw1 != pw2:
                st.error("Passwords aren't identical.")
                return
            
        pw_to_store = stored_pw
    
        if pw1 == pw2:
            pw_to_store = bcrypt.hashpw(pw1.encode('utf-8'), bcrypt.gensalt())

        try:
            c = conn.cursor()
            c.execute("""
                UPDATE users
                SET email = ?, password = ?
                WHERE username = ?
            """, (new_email, pw_to_store, user_id))

            conn.commit()
            st.success("Profile has been updated successfully.")
            time.sleep(2)
            st.rerun()

        except pyodbc.Error as e:
            st.error(f"Update failed due to a database error: {e}")
        except Exception as e:
            st.error(f"Unexpected Error during update: {e}")
        finally:
            conn.close()

    #if new_username != username:
        #st.session_state["username"] = new_username

    #st.success("Profile has been updated")
    #time.sleep(2)
    #st.rerun()

### Creates table for admin dashboard to see all registered managers/users ###
def get_users_under_me() -> pd.DataFrame | None:
    if "role_sortkey" not in st.session_state:
        return None

    current = st.session_state["role_sortkey"]
    conn = connect() # Stellt die pyodbc-Verbindung her
    if not conn:
        return None 

    try:
        sql_query = """
            SELECT u.username, u.email, u.role, r.sortkey, u.manager_ID
            FROM users u
            JOIN roles r ON u.role = r.role
            WHERE r.sortkey < ? 
            ORDER BY r.sortkey DESC, u.username
        """
        
        # NUTZT pd.read_sql: Liest die Daten direkt von der DB in den DataFrame
        df = pd.read_sql(
            sql_query, 
            conn, 
            params=(current,) # Parameter (der aktuelle sortkey) als Tupel übergeben
        )

        # Erstelle den DataFrame nur, wenn `rows` nicht leer ist
        if not df.empty:
            return df
        #else:
            #return pd.DataFrame(columns=["username", "email", "role", "sortkey", "manager_ID"])

    finally:
        conn.close()
    #conn.close()

    #return pd.DataFrame(rows, columns=["username", "email", "role", "sortkey", "manager_ID"])