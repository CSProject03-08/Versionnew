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

def employee_listview():
    """
    Returns all trips assigned to a given user (employee)
    using the user_trips mapping table.
    """
    conn = connect()
    user_id = int(st.session_state["user_ID"])
    trip_df = pd.read_sql_query("""
        SELECT 
        t.trip_ID,
        t.origin,
        t.destination,
        t.start_date,
        t.end_date,
        t.start_time,
        t.end_time,
        t.occasion
        FROM trips t
        JOIN user_trips ut ON t.trip_ID = ut.trip_ID
        WHERE ut.user_ID = ?
        ORDER BY t.start_date ASC
        """, conn, params=(user_id,))
    conn.close()

    if trip_df.empty:
        st.info("No trips assigned yet.")
        return
    
    for _, row in trip_df.iterrows():
        with st.expander(
            f"{row.trip_ID}: - {row.origin} → {row.destination} ({row.start_date} → {row.end_date})",
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
