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
    SERVER_NAME = st.secrets["azure_db"]["SERVER_NAME"]
    DATABASE_NAME = st.secrets["azure_db"]["DATABASE_NAME"]
    USERNAME = st.secrets["azure_db"]["USERNAME"]
    PASSWORD = st.secrets["azure_db"]["PASSWORD"]
    
    CONNECTION_STRING = (
        'DRIVER={ODBC Driver 18 for SQL Server};'
        f'SERVER={SERVER_NAME};'
        f'DATABASE={DATABASE_NAME};'
        f'UID={USERNAME};'
        f'PWD={PASSWORD};'
        'Encrypt=yes;'  
        'TrustServerCertificate=no;'
    )
    return CONNECTION_STRING

   
