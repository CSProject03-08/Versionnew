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
from sqlalchemy import create_engine
import urllib
from utils import load_secrets

CONNECTION_STRING = load_secrets()
connect_uri = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(CONNECTION_STRING)
engine = create_engine(connect_uri, fast_executemany=True)


def create_trip_dropdown(title: str = "Create new trip"): 
    """This function creates the expander with the form for the creation of a new trip.
    
    Args:
        None
    
    Returns:
        None
    """
    if "transport_comparison_done" not in st.session_state:
        st.session_state["transport_comparison_done"] = False

    # If a previous submission requested a clear, pop widget-backed keys before widgets are created
    if st.session_state.get("trip_clear_requested", False):
        for _k in [
            "trip_origin", "trip_destination", "trip_start_date", "trip_end_date",
            "trip_start_time", "trip_end_time", "trip_occasion", "trip_users",
            "trip_transport_method"
        ]:
            st.session_state.pop(_k, None)
        st.session_state["transport_comparison_done"] = False
        st.session_state["trip_clear_requested"] = False

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
                 st.session_state[key] = ""
            else:
                 st.session_state[key] = ""

    with st.expander(title, expanded=False):

        # Trip Form: details => users => API key => comparison => transport choice => invite
        with st.form("Create a trip", clear_on_submit=False):

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
            
            user_df = pd.read_sql_query("""
                SELECT u.user_ID, u.username FROM users u 
                JOIN roles r ON u.role = r.role 
                WHERE r.sortkey < 3
                AND u.manager_ID = ? 
                ORDER BY username""", engine, params=(manager_ID,),
            )

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
                # we don't set a global here; the chosen value is kept in session_state under key 'trip_transport_method'
                pass

            if not comparison_ready:
                st.caption(
                    "Choose a transportation option after entering the API key and updating the comparison."
                )

            submitted = st.form_submit_button("Invite", type="primary")

        # handle the submit after the form block to ensure we read final values from session_state
        if submitted:
            origin = st.session_state.get("trip_origin", "")
            if not origin:
                st.error("Origin is required")
            else:
                destination = st.session_state.get("trip_destination", "")
                start_date = st.session_state.get("trip_start_date")
                end_date = st.session_state.get("trip_end_date")
                start_time_val = st.session_state.get("trip_start_time")
                end_time_val = st.session_state.get("trip_end_time")
                start_time_str = start_time_val.strftime("%H:%M") if start_time_val is not None else ""
                end_time_str = end_time_val.strftime("%H:%M") if end_time_val is not None else ""
                occasion = st.session_state.get("trip_occasion", "")
                manager_ID = int(st.session_state.get("user_ID"))
                selected = st.session_state.get("trip_users", [])
                user_ids = [opt[0] for opt in selected]

                transport_choice = st.session_state.get("trip_transport_method", "Car")
                method_transport = 0 if transport_choice == "Car" else 1

                # call add_trip with values from session_state
                try:
                    add_trip(origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, user_ids, method_transport)
                    # request a safe clear before the next widgets are created and rerun
                    st.session_state["trip_clear_requested"] = True
                    st.session_state["transport_comparison_done"] = False
                    st.success("Invited and data cleared!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add trip: {e}")
