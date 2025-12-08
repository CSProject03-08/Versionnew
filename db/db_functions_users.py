"""db_function_users.py defines the necessary functions for the whole user-management, including creation of the roles Admin, Manager and User/Employee. It includes functions for adding users, editing user data, deleting users, fetching user data based on credentials as well as
initializing the database tables."""

import pyodbc
import time
import streamlit as st
import pandas as pd
import bcrypt
from sqlalchemy import create_engine

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

def create_tables():
    """Creates the tables 'roles' and 'users' in the database if they do not already exist. 
    
    Args:
        None
        
    Returns:
        None
    """
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    # Table roles must be created first because of foreign key in Users table. Roles table has role and sortkey, where sortkey defines hierarchy.
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
        print("Tabelle 'roles' erstellt oder existiert bereits.") #feedback
    except pyodbc.Error as e:
        print(f"Fehler beim Erstellen von 'roles': {e}") #error if table creation fails
        pass


    # Create users table, with user_ID, username, password, email, role and manager_ID.
    try:
        # IDENTITY(1,1) is the same as AUTOINCREMENT in SQLite.
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
        print("Table 'users' has been created! or already exists.") #feedback
    except pyodbc.Error as e:
        print(f"Creating table 'users' failed!: {e}") #error if table creation fails
        pass

    conn.commit()
    conn.close()


def initialize_data():
    """Dummy Data used while development phase, remove or comment out in production. Admin will be defined in st.secrets later on.
    Args:
        None
        
    Returns:
        None
    """
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()

    roles_to_insert = [
        ("Administrator", 3),
        ("Manager", 2),
        ("User", 1)
    ]
    
    for role_name, sortkey_val in roles_to_insert:
        # Checks first if role already exists, if not insert it
        try:
            c.execute("""
                IF NOT EXISTS (SELECT 1 FROM roles WHERE role = ?)
                BEGIN
                    INSERT INTO roles (role, sortkey) VALUES (?, ?)
                END
            """, role_name, role_name, sortkey_val)
        except pyodbc.Error as e:
            # error if role insertion fails
            print(f"Fail to insert data {role_name}: {e}")
            pass      
    conn.commit()
    conn.close()

def get_user(username):
    """Fetches user data based on the provided username.
    Args:
        username (str): The username of the user to fetch.
        
    Returns:
        tuple: User data if found, else None.
    """
    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data


def get_user_ID(username: str):
    """ Used to get the User-ID of the Managers, to create Manager_ID column in  users.db, to be able to groupt the all app-users according to the manager which created them.
    Args:
        username (str): The username of the user to fetch the ID for.
        
    Returns:
        int: User ID if found, else None.
    """

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
    """ Used to get the Manager_ID of a user based on their username.
    Args:
        username (str): The username of the user to fetch the Manager_ID for.
    
    Returns:
        int: Manager ID if found, else None.
    """

    conn = connect()
    if conn is None:
        return
    c = conn.cursor()
    c.execute("SELECT manager_ID FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def add_user(username, password, email, role):
    """Adds a new user to the database with the provided details.
    Args:
        username (str): The username of the new user.
        password (str): The password of the new user. (econded with bcrypt)
        email (str): The email of the new user.
        role (str): The role of the new user.
    
    Returns:
        None, however adds user to database.
    """

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()) #encode password with bcrypt
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
#def get_user_by_credentials_old(username, password):
#    """Fetches user data based on the provided username and password.
#    Args:
#        username (str): The username of the user to fetch.
#        password (str): The password of the user to fetch.
#    
#    Returns:
#        tuple: User data if found, else None.
#    """
#    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
#    conn = connect()
#    if conn is None:
#        return
#    c = conn.cursor()
#    c.execute(
#        "SELECT username, role FROM users WHERE username = ? AND password = ?",
#    )
#        (username, hashed_pw)
#    user = c.fetchone()
#    conn.close()
#    return user

def get_user_by_credentials(username, password):
    """Fetches user data based on the provided username and password.
    Args:
        username (str): The username of the user to fetch.
        password (str): The password of the user to fetch.      
    
    Returns:
        tuple: User data if found, else None.
    """

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


def get_role_sortkey(role):
    """Fetches the sortkey for a given role.
    Args:
        role (str): The role to fetch the sortkey for.
        
    Returns:
        int: Sortkey if found, else None.
    """
    
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


def list_roles_editable():
    """Lists all roles that are editable based on the current user's role sortkey(editable users: all under own sortkey).
    Args:
        None
    
    Returns:
        list: List of editable roles.
    """
    
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

def get_users_for_current_manager():
    """Fetches all users created by the current manager.
    Args:
        None

    Returns:
        list: List of users created by the current manager.
    """   

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


def register_user_dropdown(title: str = "Register new user"):
    """Dropdown form in Streamlit to register a new user, accessible by managers.
     Args:
        title (str): The title of the dropdown form.
        
    Returns:
        None
    """

    if "role_sortkey" not in st.session_state:
        st.warning("You're not authorized to add new users")
        return

    roles = list_roles_editable()
    role_names = [r[0] for r in roles]
    # Dropdown form in Streamlit
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
        # Process form submission
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
            # Try to add user and handle potential database errors
            try:
                add_user(username, password, email, role)
                st.success(f"User **{username}** was registered")
                time.sleep(2)
                st.rerun()
            except pyodbc.Error as e:
                st.error(f"Registration failed due to a database error: {e}")
            except Exception as e:
                st.error(f"Unexpected Error: {e}")


def register_user_dropdown_admin(title: str = "Register new user"):
    """Dropdown form in Streamlit to register a new user, accessible by Admins.
     Args:
        title (str): The title of the dropdown form.
        
    Returns:
        None
    """

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


def del_user_dropdown(title: str = "Delete user"):
    """Dropdown in Streamlit to delete a user, accessible by managers.
     Args:
        title (str): The title of the dropdown form.
    
    Returns:
        None
    """

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

def del_user_dropdown_admin(title: str = "Delete user"):
    """Dropdown in Streamlit to delete a user, accessible by Admins.
     Args:
        title (str): The title of the dropdown form.

    Returns:
        None
    """
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

def edit_user_dropdown(title: str = "Edit user"):
    """Dropdown in Streamlit to edit a user, accessible by managers.
     Args:
        title (str): The title of the dropdown form.
        
    Returns:
        None
    """
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
        selected_user_data = next((u for u in users if u[0] == selected_user), None) #should give queried datapoints back

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
        # Set default index for role selection
        try:
            default_role_index = editable_role_names.index(current_role)
        except ValueError:
            # If current role not found in editable roles, default to first role
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
                if not new_username:
                    st.error("Username cannot be empty.")
                    return
                if new_role not in editable_role_names:
                    st.error("Invalid role selected.")
                    return

                if new_password:
                    # hash new password
                    pw_to_store = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                else:
                    pw_to_store = current_password

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
                    # catches invalide entries (i.e. doubled username)
                    st.error(f"Update failed due to a database error: Check if the new username '{new_username}' already exists or if the role is valid. Details: {e}")
                except Exception as e:
                    st.error(f"Unexpected Error during update: {e}")
                finally:
                    conn.close()

def edit_user_dropdown_admin(title: str = "Edit user"):
    """Dropdown in Streamlit to edit a user, accessible by Admins.
     Args:
        title (str): The title of the dropdown form.

    Returns:
        None
    """
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
        selected_user_data = next((u for u in users if u[0] == selected_user), None) #should give queried datapoints back

        if not selected_user_data:
            st.warning("User not found yet.")
            return

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

def register_main(title: str = "Register as manager"):
    """Dropdown form in Streamlit to register a new manager, accessible by anyone.
     Args:
        title (str): The title of the dropdown form.   

    Returns:
        None
    """

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

def edit_own_profile(title: str = "My profile"):
    """Form in Streamlit to edit own user profile.
     Args:
        title (str): The title of the form.

    Returns:
        None
    """
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
        st.session_state["username"] = original_username #check wether session-state is at current

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



def get_users_under_me() -> pd.DataFrame | None:
    """Creates table for admin dashboard to see all registered managers/users.
    Args:
        None

    Returns:
        pd.DataFrame;  None: DataFrame containing user data if found, else None.
    """
    if "role_sortkey" not in st.session_state:
        return None

    current = st.session_state["role_sortkey"]
    conn = connect()
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
        
        # uses pandas to read the sql query into a DataFrame
        df = pd.read_sql_query(
            sql_query, 
            conn, 
            params=(current,) # params as tuple
        )
        if not df.empty:
            return df

    finally:
        conn.close()


##################################################################
# non-database related user functions below
##################################################################
def logout():
    """Logs out the user and redirects to main.py.
    Args:
        None    
        
    Returns:
        None
    """
    if st.button(" Logout", type="secondary"):
        # deletes data related to session states
        for key in ["user_ID", "role", "username"]:
            if key in st.session_state:
                del st.session_state[key]

        st.success("You have been logged out.")

        # redirects to main.py
        st.switch_page("main.py")

import streamlit as st

def hide_sidebar():
    """Completely hides the Streamlit sidebar, including the toggle button."""
    hide_sidebar_css = """
        <style>
            /* Hide the sidebar itself */
            [data-testid="stSidebar"] {
                display: none !important;
            }

            /* Hide the little toggle arrow */
            [data-testid="stSidebarNav"] {
                display: none !important;
            }

            /* Hide the entire sidebar container */
            section[data-testid="stSidebar"] {
                display: none !important;
            }
        </style>
    """
    st.markdown(hide_sidebar_css, unsafe_allow_html=True)