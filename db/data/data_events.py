import streamlit as st
import sqlite3
from pathlib import Path

# Connect directly to SQLite database
db_path = Path(__file__).parent.parent / 'horizon.db'
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row  # Return rows as dictionaries
cursor = conn.cursor()

st.set_page_config(page_title="Data Imports for Events and Trips", page_icon="📥") 

'Data Imports for Events and Trips'

# Query trips directly
cursor.execute("SELECT * FROM trips WHERE id = ?", (1,))
trip_result = cursor.fetchone()
st.write("Trip Details:", dict(trip_result) if trip_result else "No trip found")

# Query events directly
cursor.execute("SELECT * FROM events WHERE id = ?", (1,))
event_result = cursor.fetchone()
st.write("Event Details:", dict(event_result) if event_result else "No event found")

conn.close()

'''Access: Admin Only'''
