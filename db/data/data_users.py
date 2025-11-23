import streamlit as st

import streamlit as st
import sqlite3
from pathlib import Path

# Connect directly to SQLite database
db_path = Path(__file__).parent.parent / 'horizon.db'
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Insert sample users
cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", 
               ("Anna", "AdminPass", "Admin"))
cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", 
               ("Bob", "ManagerPass", "Manager"))
cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", 
               ("Charlie", "EmployeePass", "Employee"))
conn.commit()

# Query to verify
cursor.execute("SELECT * FROM users WHERE id = ?", (3,))
user = cursor.fetchone()
st.write("Employee User:", dict(user) if user else "No user found")

conn.close()    
