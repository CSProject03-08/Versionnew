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
from api.dij_weather import show_trip_weather
from sqlalchemy import create_engine
from api.News import news_widget

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
            """, conn, params=(user_id, date.today()))
    
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

            c1, c2 = st.columns(2)
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
            conn = connect()
            if conn:
                try:
                    participants = pd.read_sql_query("""
                        SELECT u.username, u.email
                        FROM users u
                        JOIN user_trips ut ON ut.user_ID = u.user_ID
                        WHERE ut.trip_ID = ?
                        ORDER BY u.username
                    """, conn, params=(row.trip_ID,))

                    st.markdown("**Participants:**")
                    st.dataframe(participants, hide_index=True, use_container_width=True)
                except pd.io.sql.DatabaseError as e:
                    st.error(f"Error fetching participants: {e}")
                finally:
                    conn.close()

                st.markdown("### Transportation Details")

                #Transport method loading
                conn = connect()
                method_row = pd.read_sql_query("""
                    SELECT method_transport FROM trips WHERE trip_ID = ?
                """, conn, params=(row.trip_ID,))
                conn.close()

                method_transport = method_row.iloc[0]["method_transport"] if not method_row.empty else None

                # calling new function
                show_transportation_details(method_transport,
                    row.origin,
                    row.destination,
                    row.start_date,
                    row.start_time)

               # st.subheader("Weather Forecast for your trips")
               # show_trip_weather(
                #    destination=row.destination,
                 #   start_date=row.start_date,
                  #  end_date=row.end_date,
                #)

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
            AND ? > end_date                      
            AND t.show_trip_e = 1
            ORDER BY t.start_date ASC
            """, conn, params=(user_id, date.today()))

    except pd.io.sql.DatabaseError as e:
        st.error(f"Error fetching past trips from database: {e}")
        return
    finally:
        conn.close()

    if trip_df.empty:
        st.info("No trips available.")
        return
    
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
            expanded=is_active
        ):
            #list details
            st.markdown(f"**Occasion:** {row.occasion}")
            st.markdown(f"**Start Date:** {row.start_date}")
            st.markdown(f"**End Date:** {row.end_date}")
            st.markdown(f"**Start Time:** {row.start_time}")
            st.markdown(f"**End Time:** {row.end_time}")

            #load participants into table
            conn = connect()
            if conn:
                try:
                    participants = pd.read_sql_query("""
                        SELECT u.username, u.email
                        FROM users u
                        JOIN user_trips ut ON ut.user_ID = u.user_ID
                        WHERE ut.trip_ID = ?
                        ORDER BY u.username
                    """, conn, params=(row.trip_ID,))

                    st.markdown("**Participants:**")
                    st.dataframe(participants, hide_index=True, use_container_width=True)

                except pd.io.sql.DatabaseError as e:
                    st.error(f"Error fetching participants: {e}")
                finally:
                    conn.close()

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
                    use_container_width=True,
                ):
                    wiz.update(
                        active_trip_id=trip_id,
                        step=1,
                        hotel_cost=0.0, hotel_files=[],
                        transport_cost=0.0, transport_files=[],
                        meals_cost=0.0, meals_files=[],
                        other_cost=0.0, other_files=[],
                    )
                    st.rerun()
            else:
                # Wizard
                st.markdown("### Add business trip expense")
                cols_hdr = st.columns([1, 1])
                with cols_hdr[0]:
                    st.markdown(
                        "Please fill each category, upload receipts and "
                        "review everything before saving."
                    )
                    st.markdown(f"**Trip date:** {start_date} – {end_date}")
                    st.markdown(f"**Destination city:** {row.destination}")
                    st.markdown(f"**Duration (days):** {duration_days}")
                with cols_hdr[1]:
                    if st.button(
                        "✖ Close",
                        use_container_width=True,
                        key=f"close_{trip_id}",
                    ):
                        wiz["active_trip_id"] = None
                        wiz["step"] = 1
                        st.rerun()

                step = wiz["step"]
                st.markdown(f"#### Expense {step} of 5")

                def _next():
                    """Advance the expense wizard to the next step."""                   
                    wiz["step"] = min(5, wiz["step"] + 1)

                def _back():
                    """Go back one step in the expense wizard."""
                    wiz["step"] = max(1, wiz["step"] - 1)

                # ---------- Step 1: Hotel ----------
                if step == 1:
                    wiz["hotel_cost"] = st.number_input(
                        "Total hotel cost (CHF)",
                        min_value=0.0,
                        step=10.0,
                        value=float(wiz["hotel_cost"]),
                        key=f"hotel_cost_{trip_id}",
                    )
                    wiz["hotel_files"] = st.file_uploader(
                        "📎 Upload hotel receipts (PDF or image)",
                        type=["pdf", "png", "jpg", "jpeg"],
                        accept_multiple_files=True,
                        key=f"hotel_files_upl_{trip_id}",
                    )
                    st.button(
                        "Next →",
                        type="primary",
                        on_click=_next,
                        key=f"next1_{trip_id}",
                    )
                    
                # ---------- Step 2: Transportation ----------
                elif step == 2:
                    wiz["transport_cost"] = st.number_input(
                        "Total transportation cost (CHF)",
                        min_value=0.0,
                        step=10.0,
                        value=float(wiz["transport_cost"]),
                        key=f"transport_cost_{trip_id}",
                    )
                    wiz["transport_files"] = st.file_uploader(
                        "📎 Upload transportation receipts (PDF or image)",
                        type=["pdf", "png", "jpg", "jpeg"],
                        accept_multiple_files=True,
                        key=f"transport_files_upl_{trip_id}",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        st.button(
                            "← Back",
                            on_click=_back,
                            use_container_width=True,
                            key=f"back2_{trip_id}",
                        )
                    with c2:
                        st.button(
                            "Next →",
                            type="primary",
                            on_click=_next,
                            use_container_width=True,
                            key=f"next2_{trip_id}",
                        )

                # ---------- Step 3: Meals ----------
                elif step == 3:
                    wiz["meals_cost"] = st.number_input(
                        "Total meals cost (CHF)",
                        min_value=0.0,
                        step=5.0,
                        value=float(wiz["meals_cost"]),
                        key=f"meals_cost_{trip_id}",
                    )
                    wiz["meals_files"] = st.file_uploader(
                        "📎 Upload meal receipts (PDF or image)",
                        type=["pdf", "png", "jpg", "jpeg"],
                        accept_multiple_files=True,
                        key=f"meals_files_upl_{trip_id}",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        st.button(
                            "← Back",
                            on_click=_back,
                            use_container_width=True,
                            key=f"back3_{trip_id}",
                        )
                    with c2:
                        st.button(
                            "Next →",
                            type="primary",
                            on_click=_next,
                            use_container_width=True,
                            key=f"next3_{trip_id}",
                        )

                # ---------- Step 4: Other ----------
                elif step == 4:
                    wiz["other_cost"] = st.number_input(
                        "Other costs (CHF)",
                        min_value=0.0,
                        step=5.0,
                        value=float(wiz["other_cost"]),
                        key=f"other_cost_{trip_id}",
                    )
                    wiz["other_files"] = st.file_uploader(
                        "📎 Upload other receipts (PDF or image)",
                        type=["pdf", "png", "jpg", "jpeg"],
                        accept_multiple_files=True,
                        key=f"other_files_upl_{trip_id}",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        st.button(
                            "← Back",
                            on_click=_back,
                            use_container_width=True,
                            key=f"back4_{trip_id}",
                        )
                    with c2:
                        st.button(
                            "Next →",
                            type="primary",
                            on_click=_next,
                            use_container_width=True,
                            key=f"next4_{trip_id}",
                        )

                # ---------- Step 5: Review & Save ----------
                elif step == 5:
                    total_cost = float(
                        wiz["hotel_cost"]
                        + wiz["transport_cost"]
                        + wiz["meals_cost"]
                        + wiz["other_cost"]
                    )
                    st.subheader("Review")
                    st.markdown(
                        f"- **Hotel:** CHF {wiz['hotel_cost']:,.2f} "
                        f"({len(wiz['hotel_files'] or [])} file(s))\n"
                        f"- **Transportation:** CHF {wiz['transport_cost']:,.2f} "
                        f"({len(wiz['transport_files'] or [])} file(s))\n"
                        f"- **Meals:** CHF {wiz['meals_cost']:,.2f} "
                        f"({len(wiz['meals_files'] or [])} file(s))\n"
                        f"- **Other:** CHF {wiz['other_cost']:,.2f} "
                        f"({len(wiz['other_files'] or [])} file(s))\n"
                    )
                    st.markdown(
                        f"**Calculated total (CHF):** {total_cost:,.2f}"
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        st.button(
                                "← Back",
                                on_click=_back,
                                use_container_width=True,
                                key=f"back5_{trip_id}",
                            )
                    with c2:
                        if st.button(
                            "Save & Retrain",
                            type="primary",
                            use_container_width=True,
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
                                step=1,
                                hotel_cost=0.0,
                                hotel_files=[],
                                transport_cost=0.0,
                                transport_files=[],
                                meals_cost=0.0,
                                meals_files=[],
                                other_cost=0.0,
                                other_files=[],
                            )

                            #archieving trips
                            try:
                                conn = connect()
                                c = conn.cursor()
                                c.execute("""UPDATE trips SET show_trip_e = 0
                                    WHERE manager_id = ?
                                    AND ? > end_date
                                """, (user_id, date.today()))
                                conn.commit()
                                st.success("Archived past trips!")
                                time.sleep(2)
                                # ---- 6. Rerun so expander shows summary instead of wizard ----
                            except pyodbc.Error as e:
                                if conn:
                                    conn.rollback()
                                    st.error(f"Datenbankfehler: Die Archivierung konnte nicht abgeschlossen werden. {e}")
        
                            except Exception as e:
                                if conn:
                                    conn.rollback()
                                    st.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

                            finally:
                                if conn:
                                    conn.close()
                                st.rerun()