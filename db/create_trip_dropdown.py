"""create_trip_dropdown.py was initially part of db_functions_trips.py but had to be moved in a seperate module
because of the global variables. The file ensures that the comparison of the travel method could be done without
loosing the inputs from the trip creation. Afterwards the sessionstate will be reseted. Doing this within one
function is not allowed."""

import pyodbc
import time
import streamlit as st
import pandas as pd
from api.api_transportation import transportation_managerview
from db.db_functions_trips import add_trip

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

def clear_trip_form_manual():
    """Clears the trip creation form and adds the trip to the database if the origin is not empty.

    Args:
        None

    Returns:
        None
    """

    if st.session_state["trip_origin"] not in "":
        add_trip(origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, user_ids, method_transport)
        st.session_state["trip_origin"] = ""
        st.session_state["trip_destination"] = ""
        st.session_state["trip_occasion"] = ""
        st.session_state["trip_users"] = []
        st.session_state["transport_comparison_done"] = False
        st.success("Invited and data cleared!")
        time.sleep(2)
        return

    else:
        raise SyntaxError


def create_trip_dropdown(title: str = "Create new trip"): 
    """This function creates the expander with the form for the creation of a new trip.
    
    Args:
        None
    
    Returns:
        None
    """
    if "transport_comparison_done" not in st.session_state:
        st.session_state["transport_comparison_done"] = False

    keys_to_init = [
        "trip_origin", "trip_destination", "trip_start_date", "trip_end_date",
        "trip_start_time", "trip_end_time", "trip_occasion", "trip_users", 
        "trip_transport_method"
    ]

    for key in keys_to_init:
        if key not in st.session_state:
            # sets default values for date, time, list and transport method
            if "date" in key:
                 st.session_state[key] = pd.to_datetime("today").date()
            elif "time" in key:
                 st.session_state[key] = pd.to_datetime("09:00").time()
            elif key == "trip_users":
                 st.session_state[key] = []
            elif key == "trip_transport_method":
                 st.session_state[key] = "Car"
            else:
                 st.session_state[key] = ""

    with st.expander(title, expanded=False):

        global method_transport

        # Trip Form: details => users => API key => comparison => transport choice => invite
        method_transport = 0  # Default: 0 = Car, 1 = Public transport

        with st.form("Create a trip", clear_on_submit=False):

            global origin
            global destination
            global start_date
            global end_date
            global start_time_str
            global end_time_str
            global occasion
            global manager_ID
            global user_ids

            # 1) Trip basics
            origin = st.text_input("Origin", key="trip_origin")
            destination = st.text_input("Destination", key="trip_destination")
            start_date = st.date_input("Departure", key="trip_start_date")
            end_date = st.date_input("Return", key="trip_end_date")
            start_time = st.time_input("Start Time", key="trip_start_time")
            end_time = st.time_input("End Time", key="trip_end_time")
            start_time_str = st.session_state["trip_start_time"].strftime("%H:%M")
            end_time_str = st.session_state["trip_end_time"].strftime("%H:%M")
            occasion = st.text_input("Occasion", key="trip_occasion")
            manager_ID = int(st.session_state["user_ID"])

            conn = connect()
            if conn is None:
                return
            
            user_df = pd.read_sql_query("""SELECT u.user_ID, u.username FROM users u 
                                        JOIN roles r ON u.role = r.role 
                                        WHERE r.sortkey < 3
                                        AND u.manager_ID = ? 
                                        ORDER BY username""", conn, params=(manager_ID,),
            )
            conn.close()

            options = list(zip(user_df["user_ID"], user_df["username"]))
            selected = st.multiselect("Assign users", options=options, format_func=lambda x: x[1], key="trip_users")
            user_ids = [opt[0] for opt in selected]

            # 2) API-Key and comparison
            st.markdown("---")
            st.subheader("Method of Transport")

            api_key = st.secrets["GOOGLE_API_KEY"]

            compare_clicked = st.form_submit_button("Do the comparison", type="secondary")

            if compare_clicked and origin and destination:
                st.session_state["transport_comparison_done"] = True
                transportation_managerview(origin, destination, api_key)
            else:
                if "transport_comparison_done" not in st.session_state:
                    st.session_state["transport_comparison_done"] = False

            comparison_ready = st.session_state.get("transport_comparison_done", False)
            # 3) Transport choice
            transport_method = st.selectbox(
                "Preferred transportation",
                ["Car", "Public transport"],
                disabled=not comparison_ready,
                key="trip_transport_method",
            )


            if comparison_ready:
                method_transport = 0 if transport_method == "Car" else 1

            if not comparison_ready:
                st.caption(
                    "Choose a transportation option after entering the API key and updating the comparison."
                )

            st.form_submit_button("Invite", type="primary", on_click=clear_trip_form_manual)
