# seed_sample_data.py
from db.db_class_users import Users
from db.db_class_locations import Locations
from db.db_class_events import Events, Trips
from db.db_class_reservations import Reservations
from db.db_connection import get_database

def seed():
    print("Connecting to database...")
    db = get_database()
    db.connect()

    # --- Instantiate classes with DB ---
    user_model = Users()
    user_model.set_db(db)

    location_model = Locations(db)
    event_model = Events(db)
    trip_model = Trips(db)
    reservation_model = Reservations(db)

    print("Seeding Users...")
    users = [
        ("admin1", "admin123", "Admin"),
        ("manager_sara", "mgr123", "Manager"),
        ("manager_luca", "mgr123", "Manager"),
        ("emma.w", "emp123", "Employee"),
        ("john.d", "emp123", "Employee"),
        ("sofia.k", "emp123", "Employee"),
    ]
    for u in users:
        user_model.create_user(*u)

    print("Seeding Locations...")
    locations = [
        ("Zurich HB", "ZH001", 8.5402, 47.3782, 500),
        ("Geneva Gare", "GE001", 6.1423, 46.2102, 350),
        ("Basel SBB", "BS001", 7.5890, 47.5474, 400),
        ("Lausanne Gare", "LS001", 6.6291, 46.5160, 280),
        ("Bern Bahnhof", "BE001", 7.4391, 46.9481, 320),
    ]
    for loc in locations:
        location_model.add_location(*loc)

    print("Seeding Events...")
    events = [
        ("Annual Strategy Summit", "2025-04-14", "2025-04-15", "Zurich"),
        ("Sales Kickoff", "2025-06-01", "2025-06-03", "Geneva"),
        ("Data Innovation Forum", "2025-09-10", "2025-09-12", "Lausanne"),
    ]
    for e in events:
        event_model.create_event(*e)

    print("Seeding Trips...")
    trips = [
        ("Client Visit UBS", "2025-03-02", "2025-03-02", "Bern", "Zurich"),
        ("Conference Attendance", "2025-04-13", "2025-04-16", "Zurich", "Geneva"),
        ("Internal Workshop", "2025-05-05", "2025-05-06", "Basel", "Lausanne"),
        ("Partner Meeting", "2025-07-11", "2025-07-11", "Zurich", "Bern"),
        ("Training Program", "2025-10-02", "2025-10-05", "Lausanne", "Geneva"),
    ]
    for t in trips:
        trip_model.plan_trip(*t)

    print("Seeding Reservations...")
    reservations = [
        (1, 4, "2025-03-01"),  # Event 1 -> User 4
        (2, 5, "2025-05-20"),  # Event 2 -> User 5
        (3, 6, "2025-08-01"),  # Event 3 -> User 6
    ]
    for r in reservations:
        reservation_model.create_reservation(*r)

    print("Seeding completed successfully!")

if __name__ == "__main__":
    seed()
