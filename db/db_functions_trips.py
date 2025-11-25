import sqlite3
import time
import streamlit as st
import pandas as pd
from datetime import date
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "users.db")

### Connecting to the database trips.db ###
def connect():
    return sqlite3.connect(DB_PATH)

def create_trip_table():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS trips (
                        trip_ID INTEGER NOT NULL UNIQUE PRIMARY KEY AUTOINCREMENT,
                        origin TEXT NOT NULL,
                        destination TEXT NOT NULL,
                        start_date TEXT,
                        end_date TEXT,
                        start_time TEXT,
                        end_time TEXT, 
                        occasion TEXT,
                        manager_ID INTEGER
    )
    """)
    conn.commit()
    conn.close()

def create_trip_users_table():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_trips (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trip_ID INTEGER NOT NULL,
                        user_ID INTEGER NOT NULL,
                        UNIQUE (user_ID, trip_ID),
                        FOREIGN KEY(trip_ID) REFERENCES trips(trip_ID) ON DELETE CASCADE,
                        FOREIGN KEY(user_ID) REFERENCES users(user_ID) ON DELETE CASCADE
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_user_trips_trip ON user_trips(trip_ID);")
    c.execute("CREATE INDEX IF NOT EXISTS ix_user_trips_user ON user_trips(user_ID);")
    conn.commit()
    conn.close()

####not used yet#### probably not necessary
def create_manager_trip_table():
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS manager_trips (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        manager_ID INTEGER NOT NULL
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

def add_trip(origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, user_ids):
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    try:
        manager_ID = int(st.session_state["user_ID"])
        c.execute(
            "INSERT INTO trips (origin, destination, start_date, end_date, start_time, end_time, occasion, manager_ID) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID)
        )
        if user_ids:
            trip_ID = c.lastrowid
            user_trips_list = [(trip_ID, user_ID) for user_ID in user_ids]
            c.executemany("INSERT OR IGNORE INTO user_trips (trip_ID, user_ID) VALUES (?, ?)", user_trips_list)
        conn.commit()
    except Exception as e:
        st.error(f"Unable to add the trip: {e}")
    finally:
        conn.close()

def del_trip(deleted_tripID: int):
    conn = connect()
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()
    try:
        c.execute(
            "DELETE FROM trips WHERE trip_ID = ?",
            (deleted_tripID,)
        )
        c.execute(
            "DELETE FROM user_trips WHERE trip_ID = ?",
            (deleted_tripID,)
        )
        conn.commit()
    except:
        st.error("Unable to delete the trip")
    finally:
        conn.close()

def create_trip_dropdown(title: str = "Create new trip"):
    with st.expander(title, expanded=False):
        with st.form("Create a trip", clear_on_submit=True):
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

            submitted = st.form_submit_button("invite")

        if submitted:
            if not destination:
                st.error("Destination must not be empty.")
            else:
                add_trip(origin, destination, start_date, end_date, start_time_str, end_time_str, occasion, manager_ID, user_ids)
                st.success("Trip saved!")
                time.sleep(0.5)
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
    manager_ID = int(st.session_state["user_ID"])
    trip_df = pd.read_sql_query("""
        SELECT trip_ID, origin, destination, start_date, end_date, start_time, end_time, occasion
        FROM trips
        WHERE manager_ID = ?
        AND ? <= end_date
        ORDER BY start_date
    """, conn, params=(manager_ID, date.today()))
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
                    c.executemany(
                        "INSERT OR IGNORE INTO user_trips (trip_ID, user_ID) VALUES (?, ?)",
                    user_trips_list
                    )

                    conn.commit()
                    conn.close()
                    st.success("Participants updated!")
                    time.sleep(0.5)
                    st.rerun()

def past_trip_list_view():

    st.subheader("Past trips")

    conn = connect()
    manager_ID = int(st.session_state["user_ID"])
    trip_df = pd.read_sql_query("""
        SELECT trip_ID, origin, destination, start_date, end_date, start_time, end_time, occasion
        FROM trips
        WHERE manager_ID = ?
        AND ? > end_date
        ORDER BY start_date
    """, conn, params=(manager_ID, date.today()))
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

    with st.form("Delete past trips"):
        deleted = st.form_submit_button("Delete past trips")

        if deleted:
            conn = connect()
            c = conn.cursor()
            manager_ID = int(st.session_state["user_ID"])
            c.execute("""DELETE FROM trips 
                WHERE manager_id = ?
                AND ? > end_date
            """, (manager_ID, date.today()))
            conn.commit()
            conn.close()
            st.success("Deleted past trips!")
            time.sleep(0.5)
            st.rerun()