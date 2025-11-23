from db.db_connection import Database
import db.data.data_events as Events 
db = Database()
db.connect()

create_event = Events.st.button("Create Sample Event")
if create_event:
    Events.cursor.execute("""
        INSERT INTO events (name, start_date, end_date, location)
        VALUES (?, ?, ?, ?)
    """, ("Sample Event", "2024-10-01", "2024-10-01", "Main Hall"))
    Events.conn.commit()
    Events.st.success("Sample event created.") 

# Verify insertion
Events.cursor.execute("SELECT * FROM events WHERE name = ?", ("Sample Event",))
event = Events.cursor.fetchone()
Events.st.write("Inserted Event:", dict(event) if event else "No event found")