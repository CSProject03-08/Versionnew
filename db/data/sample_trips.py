"""Add sample trip data for testing"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.db_connection import Database

# Connect to database
db = Database()
db.connect()

# Sample trips data
sample_trips = [
    {
        'employee_name': 'John Smith',
        'departure_location': 'New York',
        'destination': 'Paris',
        'departure_time': '2025-12-15 08:00:00',
        'arrival_time': '2025-12-15 20:00:00',
        'status': 'confirmed'
    },
    {
        'employee_name': 'Jane Doe',
        'departure_location': 'London',
        'destination': 'Tokyo',
        'departure_time': '2025-12-20 14:30:00',
        'arrival_time': '2025-12-21 09:00:00',
        'status': 'confirmed'
    },
    {
        'employee_name': 'Alice Johnson',
        'departure_location': 'San Francisco',
        'destination': 'New York',
        'departure_time': '2025-11-25 06:00:00',
        'arrival_time': '2025-11-25 14:30:00',
        'status': 'confirmed'
    },
    {
        'employee_name': 'Bob Williams',
        'departure_location': 'Berlin',
        'destination': 'Madrid',
        'departure_time': '2025-12-01 10:00:00',
        'arrival_time': '2025-12-01 13:00:00',
        'status': 'pending'
    },
    {
        'employee_name': 'Emma Davis',
        'departure_location': 'Sydney',
        'destination': 'Singapore',
        'departure_time': '2025-12-15 22:00:00',
        'arrival_time': '2025-12-16 04:00:00',
        'status': 'confirmed'
    }
]

# Insert sample trips
print("Inserting sample trips...")
for trip in sample_trips:
    query = """
        INSERT INTO trips (employee_name, departure_location, destination, departure_time, arrival_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    db.execute(query, (
        trip['employee_name'],
        trip['departure_location'],
        trip['destination'],
        trip['departure_time'],
        trip['arrival_time'],
        trip['status']
    ))

db.commit()
print(f"✅ Successfully inserted {len(sample_trips)} sample trips!")

# Verify
db.execute("SELECT COUNT(*) FROM trips")
count = db.fetchone()[0]
print(f"Total trips in database: {count}")

db.close()
