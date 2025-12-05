import pyodbc
import time
import streamlit as st
import pandas as pd
from datetime import date
from api.api_city_lookup import get_city_coords
from geopy.distance import geodesic
from ml.ml_model import load_model
from api.api_transportation import transportation_managerview

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

### Connecting to the database ###
def connect():
    """Connects to Azure SQL-Datenbank"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # show the error
        st.error(f"Connection error: {sqlstate}")
        return None


### Creating necessary tables for trips ###
def create_trip_table():
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
    conn = connect()
    if conn is None:
        return

    c = conn.cursor()
    
    try:
        # Existenzprüfung für 'user_trips'
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
        st.error(f"Failed to create table 'user_trips': {e}")
        conn.close()
        return

    # creates index only if not exists
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
        st.error(f"Failed to create indexes for 'user_trips': {e}")
        
    finally:
        conn.close()

####not used yet#### probably not necessary
def create_manager_trip_table():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS manager_trips (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        manager_ID INTEGER NOT NULL,
                        trip_ID NOT NULL
                        UNIQUE (manager_ID, trip_ID),
                        FOREIGN KEY(manager_ID) REFERENCES users(manager_ID) ON DELETE CASCADE,
                        FOREIGN KEY(trip_ID) REFERENCES trips(trip_ID) ON DELETE CASCADE
    ) 
    """)
    conn.commit()
    conn.close()

####not used yet#### probably not necessary
def get_trips_for_current_manager():
    if "user_ID" not in st.session_state:
        return []

    manager_id = int(st.session_state["user_ID"])

    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT destination, start_date, end_date, occasion
        FROM trips t
        JOIN manager_trips m
        ON t.trip_ID = m.trip_ID
        WHERE manager_ID = ?
        ORDER BY start_date
    """, (manager_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_trip(origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, user_ids, method_transport:int):
    conn = connect()
    if conn is None:
        return
    
    c = conn.cursor()
    try:
        manager_ID = int(st.session_state["user_ID"])

        c.execute(
            "INSERT INTO trips (origin, destination, start_date, end_date, start_time, end_time, occasion, manager_ID, method_transport) "
            "OUTPUT INSERTED.trip_ID "  # Azure mechanism to return the latest trip_ID
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, method_transport)
        )
        
        if user_ids:
            # replaces c.lastrowid from Sqlite
            trip_ID = c.fetchone()[0]

            user_trips_list = [(trip_ID, user_ID) for user_ID in user_ids]
            c.executemany("INSERT INTO user_trips (trip_ID, user_ID) VALUES (?, ?)", user_trips_list)
            
        conn.commit()
    except Exception as e:
        conn.rollback() # often used with pyodbc
        st.error(f"Unable to add the trip: {e}")
    finally:
        conn.close()

def del_trip(deleted_tripID: int):
    conn = connect()
    if conn is None:
        return
    
    c = conn.cursor()
    try:
        c.execute(
            "DELETE FROM user_trips WHERE trip_ID = ?",
            (deleted_tripID,)
        )
        
        # not necessary because of ON DELETE CASCADE but for backup reasons left
        c.execute(
            "DELETE FROM trips WHERE trip_ID = ?",
            (deleted_tripID,)
        )
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Unable to delete the trip: {e}")
    finally:
        conn.close()

def create_trip_dropdown(title: str = "Create new trip"):
    with st.expander(title, expanded=False):

        # ----------------------------------------------------
        # TRIP FORM: details → users → API key → comparison → transport choice → invite
        # ----------------------------------------------------
        method_transport = 0  # Default: 0 = Car, 1 = Public transport

        with st.form("Create a trip", clear_on_submit=True):

            # 1) Trip basics
            origin = st.text_input("Origin")
            destination = st.text_input("Destination")
            start_date = st.date_input("Departure")
            end_date = st.date_input("Return")
            start_time = st.time_input("Start Time")
            end_time = st.time_input("End Time")
            start_time_str = start_time.strftime("%H:%M")
            end_time_str = end_time.strftime("%H:%M")
            occasion = st.text_input("Occasion")
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
            selected = st.multiselect("Assign users", options=options, format_func=lambda x: x[1])
            user_ids = [opt[0] for opt in selected]

            # 2) API-Key und Vergleich
            st.markdown("---")
            st.subheader("Method of Transport")

            api_key = st.secrets["GOOGLE_API_KEY"]

            compare_clicked = st.form_submit_button("Do the comparison")

            if compare_clicked and origin and destination:
                st.session_state["transport_comparison_done"] = True
                transportation_managerview(origin, destination, api_key)
            else:
                if "transport_comparison_done" not in st.session_state:
                    st.session_state["transport_comparison_done"] = False

            comparison_ready = st.session_state.get("transport_comparison_done", False)
            # 3) Auswahl der bevorzugten Transportmethode (zuerst ausgegraut)
            transport_method = st.selectbox(
                "Preferred transportation",
                ["Car", "Public transport"],
                disabled=not comparison_ready,
            )

            if comparison_ready:
                method_transport = 0 if transport_method == "Car" else 1

            if not comparison_ready:
                st.caption(
                    "🔒 Choose a transportation option after entering the API key and updating the comparison."
                )

            invite_clicked = st.form_submit_button("Invite")

            # ----------------------------------------------------
            # TRIP SPEICHERN (außerhalb des Forms, aber abhängig von invite_clicked)
            # ----------------------------------------------------
            if invite_clicked:
                if not destination:
                    st.error("Destination must not be empty.")
                else:
                    add_trip(origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, user_ids, method_transport)
                    st.success("Trip saved!")
                    time.sleep(2)
                    st.rerun()

def del_trip_dropdown(title: str = "Delete trip"):
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
                        time.sleep(0.5)
                        st.rerun()

#trip table overview
def trip_list_view():
    conn = connect()
    if conn is None:
        return
    manager_ID = int(st.session_state["user_ID"])
    trip_df = pd.read_sql_query("""
        SELECT trip_ID, origin, destination, start_date, end_date, start_time, end_time, occasion
        FROM trips
        WHERE manager_ID = ?
        AND CAST(GETDATE() AS DATE) <= end_date
        AND show_trip_m = 1
        ORDER BY start_date
    """, conn, params=(manager_ID,))
    conn.close()

    if trip_df.empty:
        st.info("No trips available.")
        return

    #loop all trips
    for _, row in trip_df.iterrows():
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
            """, conn, params=(row.trip_ID,))
            conn.close()

            st.markdown("**Participants:**")
            st.dataframe(participants, hide_index=True, use_container_width=True)

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

            #edit occasion
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
                    time.sleep(0.5)
                    st.rerun()
            
            with st.form(f"edit_participants_{row.trip_ID}"):
                st.write("Manage participants")

                #load participants to edit them
                conn = connect()
                all_users_df = pd.read_sql_query("""SELECT u.user_ID, u.username FROM users u 
                    WHERE u.manager_ID = ? 
                    ORDER BY username
                """, conn, params=(int(st.session_state["user_ID"]),),
                )
                conn.close()

                #load current participants from db
                conn = connect()
                current_df = pd.read_sql_query("""
                    SELECT u.user_ID, u.username
                    FROM users u
                    JOIN user_trips ut ON ut.user_ID = u.user_ID
                    WHERE ut.trip_ID = ?
                    AND u.manager_ID = ?
                """, conn, params=(row.trip_ID, int(st.session_state["user_ID"]),), 
                )
                conn.close()

                #multiselect to choose from
                selected_users = st.multiselect(
                    "Select participants",
                    options=all_users_df["user_ID"].tolist(),
                    default=current_df["user_ID"].tolist(),
                    format_func=lambda uid: all_users_df.loc[all_users_df["user_ID"] == uid, "username"].values[0]
                )

                #submit button
                update_participants = st.form_submit_button("Update participants")

                if update_participants:
                    conn = connect()
                    c = conn.cursor()

                    #delete old connection
                    c.execute("DELETE FROM user_trips WHERE trip_ID = ?", (row.trip_ID,))

                    #create new connection
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
                            time.sleep(0.5)
                            st.rerun()

def past_trip_list_view():

    st.subheader("Past trips")

    conn = connect()
    if conn is None:
        return
    manager_ID = int(st.session_state["user_ID"])
    trip_df = pd.read_sql_query("""
        SELECT trip_ID, origin, destination, start_date, end_date, start_time, end_time, occasion
        FROM trips
        WHERE manager_ID = ?
        AND CAST(GETDATE() AS DATE) > end_date
        AND show_trip_m = 1
        ORDER BY start_date
    """, conn, params=(manager_ID,))
    conn.close()

    if trip_df.empty:
        st.info("No trips available.")
        return

    #loop all trips
    for _, row in trip_df.iterrows():
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
            """, conn, params=(row.trip_ID,))
            conn.close()

            st.markdown("**Participants:**")
            st.dataframe(participants, hide_index=True, use_container_width=True)

    with st.form("Archive past trips"):
        archived = st.form_submit_button("Archive past trips")

        if archived:
            conn = connect()
            if conn is None:
                return
            c = conn.cursor()
            manager_ID = int(st.session_state["user_ID"])
            c.execute("""UPDATE trips SET show_trip_m = 0
                WHERE manager_id = ?
                AND CAST(GETDATE() AS DATE) > end_date
            """, (manager_ID,))
            conn.commit()
            conn.close()
            st.success("Archived past trips!")
            time.sleep(0.5)
            st.rerun()

def del_trip_forever():
         
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