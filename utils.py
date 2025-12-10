"""utils.py contains utility functions for the Streamlit application, including user logout,
hiding the sidebar, and loading secrets based on the operating system."""

import platform

def logout():
    """Logs out the user and redirects to main.py.
    Args:
        None    
        
    Returns:
        None
    """
    if st.button("Logout", key="redirect"):
        # deletes data related to session states
        for key in ["user_ID", "role", "username"]:
            if key in st.session_state:
                del st.session_state[key]

        st.success("You have been logged out.")

        # redirects to main.py
        st.switch_page("main.py")

import streamlit as st

def hide_sidebar():
    """Completely hides the Streamlit sidebar, including the toggle button.
    
    Args:
        None
        
    Returns:
        None
    """
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

def load_secrets():
    """Switches between different ODBC drivers based on the operating system. This function was not
    written by the author of this project. It was created with the help of a third-party person.
    
    Args:
        None
        
    Returns:
        odbc_str (str): ODBC connection string for the appropriate operating system.
    """
    # Find operating system
    current_os = platform.system()

    #macOS ("Darwin")
    if current_os == "Darwin":
        AZ = st.secrets["azure_db"]
        server = AZ["SERVER_NAME"]
        database = AZ["DATABASE_NAME"]
        username = AZ["USERNAME"]
        password = AZ["PASSWORD"]

        # SQLAlchemy engine
        odbc_str = (
            "DRIVER=/opt/homebrew/lib/libmsodbcsql.18.dylib;"
            f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
            "Encrypt=yes;TrustServerCertificate=no;"
        )
        return odbc_str

    # Other drivers
    else:
        AZ = st.secrets["azure_db"]
        server = AZ["SERVER_NAME"]
        database = AZ["DATABASE_NAME"]
        username = AZ["USERNAME"]
        password = AZ["PASSWORD"]

        # SQLAlchemy engine
        odbc_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
            "Encrypt=yes;TrustServerCertificate=no;"
        )
        return odbc_str
