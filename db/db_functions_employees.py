"""db_function_employees.py defines the necessary functions, mainly used in the user_overview.py. Most of the functions take the data from users.db and show/visualize it."""

import pyodbc
import time
import streamlit as st
import pandas as pd
from api.api_city_lookup import get_city_coords
from ml.ml_model import retrain_model
from db.expenses_user import insert_expense_for_training
from datetime import date, datetime, time as dtime
from geopy.distance import geodesic
#from api.weather import weather_widget
from api.api_transportation import show_transportation_details
from api.api_weather import show_trip_weather
from sqlalchemy import create_engine
import urllib
from api.api_news import news_widget
from utils import load_secrets


CONNECTION_STRING = load_secrets()
connect_uri = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(CONNECTION_STRING)
engine = create_engine(connect_uri, fast_executemany=True)

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
        # show the error
        st.error(f"Connection error: {sqlstate}")
        return None

def employee_listview():
    """
    Returns all trips assigned to a given user (employee) using the user_trips mapping table.
    Args:
        None
    Returns:
        None
    """
    if "user_ID" not in st.session_state:
        st.warning("Please log in to see your trips.")
        return

    try:
        user_id = int(st.session_state["user_ID"])
    except ValueError:
        st.error("Invalid User ID format in session state.")
        return

    conn = connect()
    if conn is None:
        st.error("Could not connect to the database.")
        return
    try:
        trip_df = pd.read_sql_query("""
            SELECT 
            t.trip_ID,
            t.origin,
            t.destination,
            t.start_date,
            t.end_date,
            t.start_time,
            t.end_time,
            t.occasion,
            t.show_trip_e
            FROM trips t
            JOIN user_trips ut ON t.trip_ID = ut.trip_ID
            WHERE ut.user_ID = ?
            AND ? <= t.end_date
            AND t.show_trip_e = 1
            ORDER BY t.start_date ASC
            """, engine, params=(user_id, date.today()))
    
    except pd.io.sql.DatabaseError as e:
        st.error(f"Error fetching trips from database: {e}")
        return
    finally:
        conn.close()

    # ---- init expense wizard state once ----
    if "expense_wizard" not in st.session_state:
        st.session_state.expense_wizard = {
            "active_trip_id": None,
            "step": 1,
            "hotel_cost": 0.0, "hotel_files": [],
            "transport_cost": 0.0, "transport_files": [],
            "meals_cost": 0.0, "meals_files": [],
            "other_cost": 0.0, "other_files": [],
        }
    wiz = st.session_state.expense_wizard

    if "expense_summaries" not in st.session_state:
        st.session_state.expense_summaries = {}  # key: trip_id, value: text
    summaries = st.session_state.expense_summaries
    
    for _, row in trip_df.iterrows():
        start_date = pd.to_datetime(row.start_date).date()
        end_date = pd.to_datetime(row.end_date).date()

        trip_id = row.trip_ID
        is_active = wiz["active_trip_id"] == trip_id

        with st.expander(
            f"{row.trip_ID}: - {row.origin} → {row.destination} ({row.start_date} → {row.end_date})",
            expanded=is_active,
        ):

            destination = row.destination

            c1, c2 = st.columns([2, 5], gap="large")
            with c1:
                st.markdown(f"**Occasion:** {row.occasion}")
                st.markdown(f"**Start Date:** {row.start_date}")
                st.markdown(f"**End Date:** {row.end_date}")
                st.markdown(f"**Start Time:** {row.start_time}")
                st.markdown(f"**End Time:** {row.end_time}")

            with c2:
                show_trip_weather(
                    destination=row.destination,
                    start_date=row.start_date,
                    end_date=row.end_date,
                )

            #load participants into table
            try:
                participants = pd.read_sql_query("""
                    SELECT u.username, u.email
                    FROM users u
                    JOIN user_trips ut ON ut.user_ID = u.user_ID
                    WHERE ut.trip_ID = ?
                    ORDER BY u.username
                """, engine, params=(row.trip_ID,))

                st.markdown("**Participants:**")
                st.dataframe(participants, hide_index=True)
            except pd.io.sql.DatabaseError as e:
                st.error(f"Error fetching participants: {e}")


                st.markdown("Transportation Details")

                #Transport method loading
                method_row = pd.read_sql_query("""
                    SELECT method_transport FROM trips WHERE trip_ID = ?
                """, engine, params=(row.trip_ID,))

                method_transport = method_row.iloc[0]["method_transport"] if not method_row.empty else None

                # calling new function
                show_transportation_details(method_transport,
                    row.origin,
                    row.destination,
                    row.start_date,
                    row.start_time)

            try:
                news_widget(destination)
    
            except Exception as e:
                st.error(f"Error: {e}")


def past_trip_view_employee():
    """
    Returns all past trips assigned to a given user (employee) using the user_trips mapping table. Also adds the expense report wizard.
    
    Args:
        None

    Returns:
        None, adding data to the db.
    """
    st.subheader("Past trips")

    if "user_ID" not in st.session_state:
        st.warning("Please log in to see your past trips.")
        return

    try:
        user_id = int(st.session_state["user_ID"])
    except ValueError:
        st.error("Invalid User ID format in session state.")
        return
        
    try:
        trip_df = pd.read_sql_query("""
            SELECT 
            t.trip_ID,
            t.origin,
            t.destination,
            t.start_date,
            t.end_date,
            t.start_time,
            t.end_time,
            t.occasion,
            t.show_trip_e
            FROM trips t
            JOIN user_trips ut ON t.trip_ID = ut.trip_ID
            WHERE ut.user_ID = ?
            AND ? > end_date                      
            AND t.show_trip_e = 1
            ORDER BY t.start_date ASC
            """, engine, params=(user_id, date.today()))

    except pd.io.sql.DatabaseError as e:
        st.error(f"Error fetching past trips from database: {e}")
        return

    if trip_df.empty:
        st.info("No trips available.")
        return
    
    # ---- init expense wizard state once ----
    if "expense_wizard" not in st.session_state:
        st.session_state.expense_wizard = {
            "active_trip_id": None,
            "hotel_cost": 0.0,
            "transport_cost": 0.0,
            "meals_cost": 0.0,
            "other_cost": 0.0,
            "all_files": [],
        }
    wiz = st.session_state.expense_wizard

    if "expense_summaries" not in st.session_state:
        st.session_state.expense_summaries = {}  # key: trip_id, value: text
    summaries = st.session_state.expense_summaries
    
    for _, row in trip_df.iterrows():
        start_date = pd.to_datetime(row.start_date).date()
        end_date = pd.to_datetime(row.end_date).date()

        trip_id = row.trip_ID
        is_active = wiz["active_trip_id"] == trip_id
        
        with st.expander(
            f"{row.trip_ID}: - {row.origin} → {row.destination} ({row.start_date} → {row.end_date})",
            expanded=is_active
        ):
            #list details
            st.markdown(f"**Occasion:** {row.occasion}")
            st.markdown(f"**Start Date:** {row.start_date}")
            st.markdown(f"**End Date:** {row.end_date}")
            st.markdown(f"**Start Time:** {row.start_time}")
            st.markdown(f"**End Time:** {row.end_time}")

            #load participants into table

            try:
                participants = pd.read_sql_query("""
                    SELECT u.username, u.email
                    FROM users u
                    JOIN user_trips ut ON ut.user_ID = u.user_ID
                    WHERE ut.trip_ID = ?
                    ORDER BY u.username
                """, engine, params=(row.trip_ID,))

                st.markdown("**Participants:**")
                st.dataframe(participants, hide_index=True)

            except pd.io.sql.DatabaseError as e:
                st.error(f"Error fetching participants: {e}")


            trip_msg = summaries.get(trip_id)
            if trip_msg:
                st.success(trip_msg)
            
            # duration in days (for ML)
            duration_days = (end_date - start_date).days + 1

            # ---- open wizard button (if not currently editing this trip) ----
            if not is_active:
                if st.button(
                    "➕ Submit expense report",
                    key=f"open_exp_{trip_id}",
                    type="primary",
                ):
                    wiz.update(
                        active_trip_id=trip_id,
                        hotel_cost=0.0,
                        transport_cost=0.0,
                        meals_cost=0.0,
                        other_cost=0.0,
                        all_files=[],
                    )
                    st.rerun()
            else:
                # Single-page Expense Report Form
                st.markdown("### Add business trip expense")
                st.markdown(
                    "Please enter all expense categories below, upload receipts, and click Save & Retrain."
                )
                st.markdown(f"**Trip date:** {start_date} – {end_date}")
                st.markdown(f"**Destination city:** {row.destination}")
                st.markdown(f"**Duration (days):** {duration_days}")

                # Close button
                if st.button(
                    "Close",
                    key=f"close_{trip_id}",
                ):
                    wiz["active_trip_id"] = None
                    st.rerun()

                st.markdown("---")

                # All expense inputs on one page
                st.subheader("Expense Details")

                wiz["hotel_cost"] = st.number_input(
                    "Total hotel cost (CHF)",
                    min_value=0.0,
                    step=10.0,
                    value=float(wiz["hotel_cost"]),
                    key=f"hotel_cost_{trip_id}",
                )

                wiz["transport_cost"] = st.number_input(
                    "Total transportation cost (CHF)",
                    min_value=0.0,
                    step=10.0,
                    value=float(wiz["transport_cost"]),
                    key=f"transport_cost_{trip_id}",
                )

                wiz["meals_cost"] = st.number_input(
                    "Total meals cost (CHF)",
                    min_value=0.0,
                    step=5.0,
                    value=float(wiz["meals_cost"]),
                    key=f"meals_cost_{trip_id}",
                )

                wiz["other_cost"] = st.number_input(
                    "Other costs (CHF)",
                    min_value=0.0,
                    step=5.0,
                    value=float(wiz["other_cost"]),
                    key=f"other_cost_{trip_id}",
                )

                # Calculate and display total immediately
                total_cost = float(
                    wiz["hotel_cost"]
                    + wiz["transport_cost"]
                    + wiz["meals_cost"]
                    + wiz["other_cost"]
                )
                st.markdown(f"### **Total (CHF): {total_cost:,.2f}**")

                st.markdown("---")
                st.subheader("Upload Receipts")
                wiz["all_files"] = st.file_uploader(
                    "📎 Upload all receipts (PDF or image)",
                    type=["pdf", "png", "jpg", "jpeg"],
                    accept_multiple_files=True,
                    key=f"all_files_upl_{trip_id}",
                )

                # Save button directly after receipts
                if st.button(
                    "Save & Retrain",
                    type="primary",
                    key=f"save_{trip_id}",
                ):
                    # ---- 1. Compute distance between origin/destination for ML ----
                    origin_city = row.origin
                    dest_city = row.destination

                    origin_coords = get_city_coords(origin_city)
                    dest_coords = get_city_coords(dest_city)

                    if origin_coords and dest_coords:
                        distance_km = geodesic(
                            origin_coords, dest_coords
                        ).km
                    else:
                        distance_km = 0.0  # fallback

                    # ---- 2. Insert row into ML training DB ----
                    insert_expense_for_training(
                        dest_city=dest_city,
                        distance_km=distance_km,
                        duration_days=duration_days,
                        total_cost=total_cost,
                        user_id=user_id,
                    )

                    # ---- 3. Retrain ML model ----
                    mae = retrain_model()

                    # ---- 4. Build and store per-trip summary ----
                    if mae is not None:
                        msg = (
                            f"Expense saved for this trip. "
                            f"Total: CHF {total_cost:,.2f}. "
                            f"Model retrained (MAE: {mae:,.2f})."
                        )
                    else:
                        msg = (
                            f"Expense saved for this trip. "
                            f"Total: CHF {total_cost:,.2f}."
                        )

                    summaries[trip_id] = msg

                    # ---- 5. Reset wizard so it closes ----
                    wiz.update(
                        active_trip_id=None,
                        hotel_cost=0.0,
                        transport_cost=0.0,
                        meals_cost=0.0,
                        other_cost=0.0,
                        all_files=[],
                    )

                    #archieving trips
                    conn = None
                    try:
                        conn = connect()
                        if conn is None:
                            st.error("Could not connect to database for archiving.")
                            st.rerun()
                            return
                        c = conn.cursor()
                        c.execute("""UPDATE trips SET show_trip_e = 0
                            WHERE trip_ID = ?
                            AND CAST(GETDATE() AS DATE) > end_date
                        """, (trip_id,))
                        conn.commit()
                        st.success("Archived past trips!")
                        time.sleep(2)
                    except pyodbc.Error as e:
                        if conn:
                            conn.rollback()
                        st.error(f"Database error: The archiving could not be. {e}")
    
                    except Exception as e:
                        if conn:
                            conn.rollback()
                        st.error(f"An unexpected error occured: {e}")

                    finally:
                        if conn:
                            conn.close()
                        st.rerun()
