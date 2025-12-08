def logout():
    """Logs out the user and redirects to main.py.
    Args:
        None    
        
    Returns:
        None
    """
    if st.button(" Logout", type="tertiary"):
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