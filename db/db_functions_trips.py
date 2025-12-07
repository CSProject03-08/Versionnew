"""db_function_trips.py defines the necessary functions to manage the trips, including createion of tables,
fetching trips for the current manager, adding and deleting trips as well as creating the dropdowns.
Those are the functions which are primerily called in the managers_overview.py"""

import pyodbc
import time
import streamlit as st
import pandas as pd
from datetime import date
from api.api_city_lookup import get_city_coords
from geopy.distance import geodesic
from ml.ml_model import load_model
from api.api_transportation import transportation_managerview
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
    except pyodbc.Error as ex: # raises error in case the connection is not possible
        sqlstate = ex.args[0]
        st.error(f"Connection error: {sqlstate}")
        return None


def create_trip_table():
    """This function creates the 'trips' table in the database if it doesn't exists already
    with all necessary columns.
    
    Args:
        None
        
    Returns:
        None
    """
    conn = connect()
    if conn is None:
        return
    
    c = conn.cursor()
    try:
        c.execute("""
            IF OBJECT_ID('trips', 'U') IS NULL 
            BEGIN
                CREATE TABLE trips (
                    trip_ID INT PRIMARY KEY IDENTITY(1,1), -- NOT NULL entfernt, da PK implizit NOT NULL ist
                    origin NVARCHAR(255) NOT NULL,
                    destination NVARCHAR(255) NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    start_time TIME,
                    end_time TIME, 
                    occasion NVARCHAR(MAX),
                    manager_ID INT,
                    show_trip_m INT NOT NULL DEFAULT 1,
                    show_trip_e INT NOT NULL DEFAULT 1,
                    method_transport INTEGER      -- 0 = Car, 1 = Public transport
                );
            END
        """)
        conn.commit()
    except Exception as e:
        st.error(f"Failed to create table 'trips': {e}")
    finally:
        conn.close()


def create_trip_users_table():
    """This function creates the 'user_trips' table in the database if it doesn't exists already.
    This table connects the 'trips' and the 'users' table in the databse. It ensures that multiple
    people can be assigned to different trips. Each user_ID, trip_ID combination is unique. It
    further creates indices for enhanced fetching speed if the database once get fuller.
    
    Args:
        None
        
    Returns:
        None
    """
    conn = connect()
    if conn is None:
        return

    c = conn.cursor()
    try:
        c.execute("""
            IF OBJECT_ID('user_trips', 'U') IS NULL
            BEGIN
                CREATE TABLE user_trips (
                    id INT PRIMARY KEY IDENTITY(1,1) NOT NULL,
                    trip_ID INT NOT NULL,
                    user_ID INT NOT NULL,
                    UNIQUE (user_ID, trip_ID),
                    FOREIGN KEY(trip_ID) REFERENCES trips(trip_ID) ON DELETE CASCADE,
                    FOREIGN KEY(user_ID) REFERENCES users(user_ID) ON DELETE CASCADE
                ); 
            END
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to create table 'user_trips': {e}")
        conn.close()
        return

    try:
        c.execute("""
            IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_user_trips_trip' AND object_id = OBJECT_ID('user_trips'))
            BEGIN
                CREATE INDEX ix_user_trips_trip ON user_trips(trip_ID);
            END
        """)
        
        c.execute("""
            IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_user_trips_user' AND object_id = OBJECT_ID('user_trips'))
            BEGIN
                CREATE INDEX ix_user_trips_user ON user_trips(user_ID);
            END
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to create indexes for 'user_trips': {e}")
        
    finally:
        conn.close()


def add_trip(origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, user_ids, method_transport:int):
    """This function creates the trip in the database and inserts into the user_trips table the unique
    combination of user_ID and trip_ID.
    
    Args:
        origin (NVARCHAR(255)): The origin of the journey
        destination (NVARCHAR(255)): The destination of the journey
        start_date (DATE): The start date of the journey
        end_date (DATE): The end date of the journey
        start_time_str (TIME): The start time of the journey
        end_time_str (TIME): The end time of the journey
        occasion (NVARCHAR(MAX)): The reason of the journey or additional information
        manager_ID (INT): The ID of the manager who creates the trip for his list (gets overwritten with the sessionstate)
        user_ids (list): A list of employee_IDs who participate
        method_transport (int): The chosen transport type by the manager (as 0 or 1)
        
    Returns:
        None
        
    """
    conn = connect()
    if conn is None:
        return
    
    c = conn.cursor()
    try:
        manager_ID = int(st.session_state["user_ID"])

        c.execute(
            "INSERT INTO trips (origin, destination, start_date, end_date, start_time, end_time, occasion, manager_ID, method_transport) "
            "OUTPUT INSERTED.trip_ID "  # Azure query to return the latest trip_ID
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, method_transport)
        )
        
        if user_ids:
            trip_ID = c.fetchone()[0] # equivalent of c.lastrowid from Sqlite

            user_trips_list = [(trip_ID, user_ID) for user_ID in user_ids] # creates list of tuples for 'user_trips' table
            c.executemany("INSERT INTO user_trips (trip_ID, user_ID) VALUES (?, ?)", user_trips_list)
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Unable to add the trip: {e}")
    finally:
        conn.close()


def del_trip(deleted_tripID: int):
    """This function deletes the trip with the given trip_ID and deletes on cascade all user_ID, trip_ID tuples
    which inherit the provided trip_ID
    
    Args:
        deleted_tripID (int): The trip_ID of the trip who should be deleted
        
    Returns:
        None
    """
    conn = connect()
    if conn is None:
        return
    
    c = conn.cursor()
    try:
        c.execute(
            "DELETE FROM trips WHERE trip_ID = ?",
            (deleted_tripID,)
        )
        
        # not necessary because of ON DELETE CASCADE but for backup reasons left
        c.execute(
            "DELETE FROM user_trips WHERE trip_ID = ?",
            (deleted_tripID,)
        )
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Unable to delete the trip: {e}")
    finally:
        conn.close()


def del_trip_dropdown(title: str = "Delete trip"):
    """This function creates the expander with the form to delete a trip.
    
    Args:
        None
        
    Returns:
        None
    """
    with st.expander(title, expanded=False):
        with st.form("Delete a trip", clear_on_submit=True):
            deleted_tripID = st.text_input("Delete trip")
            deleted = st.form_submit_button("delete")

            if deleted:
                if not deleted_tripID:
                    st.error("TRIP ID must be given.")
                else:
                    try:
                        deleted_tripID = int(deleted_tripID)
                    except ValueError:
                        st.error("TRIP ID has to be a integer")
                    else:
                        del_trip(deleted_tripID)
                        st.success("Trip deleted!")
                        time.sleep(2)
                        st.rerun()


def trip_list_view():
    """This function creates the current list view of false expnaded trips for the manager.
    If expanded all the necessary information i.e. occasion, start and end date, start and
    end time as well as a dataframe with the assigned employees and the cost forecast are 
    displayed. As a small feature the assigned employees and the occasion can be edited at
    every stage. The trips are filtered by the manager_ID which is found in the session_state.
    
    Args:
        None
        
    Returns:
        None
    """
    conn = connect()
    if conn is None:
        return
    
    manager_ID = int(st.session_state["user_ID"]) # getting the parameter for the query

    # dataframe only for trips whos end dates aren't in the past
    trip_df = pd.read_sql_query("""
        SELECT trip_ID, origin, destination, start_date, end_date, start_time, end_time, occasion
        FROM trips
        WHERE manager_ID = ?
        AND CAST(GETDATE() AS DATE) <= end_date
        AND show_trip_m = 1
        ORDER BY start_date
    """, engine, params=(manager_ID,))
    conn.close()

    if trip_df.empty:
        st.info("No trips available.")
        return

    for _, row in trip_df.iterrows(): # loop all trips to create the expander
        with st.expander(
            f"{row.trip_ID} — {row.origin} → {row.destination} ({row.start_date} → {row.end_date})",
            expanded=False
        ):
            #list details
            st.write("**Occasion:**", row.occasion)
            st.write("**Start Date:**", row.start_date)
            st.write("**End Date:**", row.end_date)
            st.write("**Start Time:**", row.start_time)
            st.write("**End Time:**", row.end_time)

            #load participants into table
            conn = connect()
            participants = pd.read_sql_query("""
                SELECT u.username, u.email
                FROM users u
                JOIN user_trips ut ON ut.user_ID = u.user_ID
                WHERE ut.trip_ID = ?
                ORDER BY u.username
            """, engine, params=(row.trip_ID,))
            conn.close()

            # display the dataframe with the participants
            st.markdown("**Participants:**")
            st.dataframe(participants, hide_index=True, width="stretch")

            # ML model for the cost forecast
            num_participants = len(participants)

            model = load_model()
            if model is not None and num_participants > 0:
                # duration in days
                try:
                    start_date_obj = pd.to_datetime(row.start_date).date()
                    end_date_obj = pd.to_datetime(row.end_date).date()
                    duration_days = (end_date_obj - start_date_obj).days + 1
                except Exception:
                    duration_days = 0

                # distance in km based on origin/destination
                origin_coords = get_city_coords(row.origin)
                dest_coords = get_city_coords(row.destination)

                if origin_coords and dest_coords:
                    distance_km = geodesic(origin_coords, dest_coords).km
                else:
                    distance_km = 0.0

                #build one-row dataframe for the model
                X_pred = pd.DataFrame([{
                    "dest_city": row.destination,
                    "distance_km": distance_km,
                    "duration_days": duration_days,
                }])

                try:
                    per_employee_cost = float(model.predict(X_pred)[0])
                    predicted_total = per_employee_cost * num_participants
                    st.metric(
                        "Predicted total trip cost for all participants (CHF)",
                        f"{predicted_total:,.2f}"
                    )
                    st.caption(
                        f"Approx. {per_employee_cost:,.2f} CHF per person."
                    )
                except Exception as e:
                    st.warning(f"Could not compute ML prediction: {e}")
            else:
                st.info(
                    "No ML model trained yet. "
                    "Once employees submit expense reports, "
                    "the model will be able to predict costs."
                )

            # edit the occasion of the trip
            with st.form(f"edit_trip_{row.trip_ID}"):
                new_occasion = st.text_input("Edit occasion", value=row.occasion)
                submitted = st.form_submit_button("Save changes")
                if submitted:
                    conn = connect()
                    conn.execute(
                        "UPDATE trips SET occasion = ? WHERE trip_ID = ?",
                        (new_occasion, row.trip_ID)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Occasion updated!")
                    time.sleep(2)
                    st.rerun()
            
            # edit participants of the trip
            with st.form(f"edit_participants_{row.trip_ID}"):
                st.write("Manage participants")

                # load all participants to edit them for options afterwards
                conn = connect()
                all_users_df = pd.read_sql_query("""SELECT u.user_ID, u.username FROM users u 
                    WHERE u.manager_ID = ? 
                    ORDER BY username
                """, engine, params=(manager_ID,),
                )
                conn.close()

                # load participants from this trip for default value afterwards
                conn = connect()
                current_df = pd.read_sql_query("""
                    SELECT u.user_ID, u.username
                    FROM users u
                    JOIN user_trips ut ON ut.user_ID = u.user_ID
                    WHERE ut.trip_ID = ?
                    AND u.manager_ID = ?
                """, engine, params=(row.trip_ID, manager_ID), 
                )
                conn.close()

                # multiselect to choose from
                selected_users = st.multiselect(
                    "Select participants",
                    options=all_users_df["user_ID"].tolist(),
                    default=current_df["user_ID"].tolist(),
                    format_func=lambda uid: all_users_df.loc[all_users_df["user_ID"] == uid, "username"].values[0] # filters only usernames to display in the multiselect
                )

                # form submit button to update
                update_participants = st.form_submit_button("Update participants")

                if update_participants:
                    conn = connect()
                    c = conn.cursor()

                    # delete all participants from the trip
                    c.execute("DELETE FROM user_trips WHERE trip_ID = ?", (row.trip_ID,))

                    # adds all new participants to the trip
                    user_trips_list = [(row.trip_ID, uid) for uid in selected_users]
                    try:
                        c.executemany(
                            "INSERT INTO user_trips (trip_ID, user_ID) VALUES (?, ?)",
                        user_trips_list
                        )

                        conn.commit()
                        st.success("Participants updated!")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Failed to update participants: {e}")
                    finally:
                        conn.close()
                        if 'st.error' not in st.session_state:
                            time.sleep(2)
                            st.rerun()


def past_trip_list_view():
    """This function lists as the function above the trip details. However, this time
    only past trips are displayed without the option to edit those trips or to have a
    cost forecast. There is the option to archive them by clicking on the foreseen 
    button. This will not delete the trips, instead they will just no longer be visible.
    
    Args:
        None
        
    Returns:
        None
    """
    st.subheader("Past trips")

    conn = connect()
    if conn is None:
        return
    
    manager_ID = int(st.session_state["user_ID"])

    # dataframe only for trips whos end dates are in the past
    trip_df = pd.read_sql_query("""
        SELECT trip_ID, origin, destination, start_date, end_date, start_time, end_time, occasion
        FROM trips
        WHERE manager_ID = ?
        AND CAST(GETDATE() AS DATE) > end_date
        AND show_trip_m = 1
        ORDER BY start_date
    """, engine, params=(manager_ID,))
    conn.close()

    if trip_df.empty:
        st.info("No trips available.")
        return

    # loop all trips for the expander
    for _, row in trip_df.iterrows():
        with st.expander(
            f"{row.trip_ID} — {row.origin} → {row.destination} ({row.start_date} → {row.end_date})",
            expanded=False
        ):
            # list details
            st.write("**Occasion:**", row.occasion)
            st.write("**Start Date:**", row.start_date)
            st.write("**End Date:**", row.end_date)
            st.write("**Start Time:**", row.start_time)
            st.write("**End Time:**", row.end_time)

            # load participants into table
            conn = connect()
            participants = pd.read_sql_query("""
                SELECT u.username, u.email
                FROM users u
                JOIN user_trips ut ON ut.user_ID = u.user_ID
                WHERE ut.trip_ID = ?
                ORDER BY u.username
            """, engine, params=(row.trip_ID,))
            conn.close()

            st.markdown("**Participants:**")
            st.dataframe(participants, hide_index=True, width="stretch")

    # form to archive the trips
    with st.form("Archive past trips"):
        archived = st.form_submit_button("Archive past trips")

        if archived:
            conn = connect()
            if conn is None:
                return
            
            c = conn.cursor()
            # by setting the show_trip_m varible to 0 those trips won't be displayed any longer
            c.execute("""UPDATE trips SET show_trip_m = 0
                WHERE manager_id = ?
                AND CAST(GETDATE() AS DATE) > end_date
            """, (manager_ID,))
            conn.commit()
            conn.close()
            st.success("Archived past trips!")
            time.sleep(2)
            st.rerun()


def del_trip_forever():
    """This fuction finally deletes tripa automatically after 365 days. As acces increases
    this number should be adjusted accordingly.
    
    Args:
        None
        
    Returns:
        None
    """
    conn = connect()
    if conn is None:
        return
    
    c = conn.cursor()
    manager_ID = int(st.session_state["user_ID"])
    try:
        c.execute("""DELETE FROM trips 
            WHERE manager_ID = ?
            AND show_trip_m = 0
            AND DATEDIFF(day, end_date, GETDATE()) > 365
        """, (manager_ID,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to delete old archived trips: {e}")
    finally:
        conn.close()