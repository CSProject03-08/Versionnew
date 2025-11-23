
"""Module for managing Events and Trips in the database."""

"Defines class: Event and subclass Trip"


class Events:

    def __init__(self):
        pass

    def __init__(self, db):
        self.db = db

    def create_event(self, event_name, start_date, end_date, city_name):
        query = "INSERT INTO events (name, start_date, end_date, location) VALUES (?, ?, ?, ?)"
        self.db.execute(query, (event_name, start_date, end_date, city_name))
        self.db.commit()    

    def get_event(self, event_id):
        query = "SELECT * FROM events WHERE id = ?"
        self.db.execute(query, (event_id,))
        return self.db.fetchone()
    
    def get_all_events(self):
        """Get all events ordered by start date"""
        query = "SELECT * FROM events ORDER BY start_date"
        self.db.execute(query)
        return self.db.fetchall()
    
    def update_event(self, event_id, name=None, date=None, location=None):
        fields = []
        values = []
        if name:
            fields.append("name = ?")
            values.append(name)
        if date:
            fields.append("date = ?")
            values.append(date)
        if location:
            fields.append("location = ?")
            values.append(location)
        values.append(event_id)
        query = f"UPDATE events SET {', '.join(fields)} WHERE id = ?"
        self.db.execute(query, tuple(values))
        self.db.commit()
    
    def delete_event(self, event_id):
        query = "DELETE FROM events WHERE id = ?"
        self.db.execute(query, (event_id,))
        self.db.commit()
    
    
class Trips(Events):
    """Trip subclass that inherits from Events"""
        
    def __init__(self, db):
        super().__init__(db)  # Call parent __init__
        self.event_type = "Trip"  # Additional attribute for Trips

    def plan_trip(self, event_name, start_date, end_date, location_name, destination):
        """Trip-specific method to plan a trip"""
        query = "INSERT INTO trips (name, start_date, end_date, location, destination) VALUES (?, ?, ?, ?, ?)"
        self.db.execute(query, (event_name, start_date, end_date, location_name, destination))
        self.db.commit()

    def get_trip(self, trip_id):
        """Trip-specific method to get trip details"""
        query = "SELECT * FROM trips WHERE id = ?"
        self.db.execute(query, (trip_id,))
        return self.db.fetchone()
    
    def update_trip(self, trip_id, name=None, date=None, location=None, destination=None):
        """Trip-specific method to update trip details"""
        fields = []
        values = []
        if name:
            fields.append("name = ?")
            values.append(name)
        if date:
            fields.append("date = ?")
            values.append(date)
        if location:
            fields.append("location = ?")
            values.append(location)
        if destination:
            fields.append("destination = ?")
            values.append(destination)
        values.append(trip_id)
        query = f"UPDATE trips SET {', '.join(fields)} WHERE id = ?"
        self.db.execute(query, tuple(values))
        self.db.commit()

    def cancel_trip(self, trip_id):
        """Trip-specific method to cancel a trip"""
        query = "DELETE FROM trips WHERE id = ?"
        self.db.execute(query, (trip_id,))
        self.db.commit()
    
    def search_trips_by_date(self, search_date):
        """Search trips by departure date"""
        query = """
            SELECT * FROM trips 
            WHERE DATE(departure_time) = DATE(?)
            ORDER BY departure_time
        """
        self.db.execute(query, (search_date,))
        return self.db.fetchall()
    
    def search_trips_by_destination(self, destination):
        """Search trips by destination (partial match)"""
        query = """
            SELECT * FROM trips 
            WHERE destination LIKE ? OR departure_location LIKE ?
            ORDER BY departure_time
        """
        search_term = f"%{destination}%"
        self.db.execute(query, (search_term, search_term))
        return self.db.fetchall()
    
    def search_trips(self, destination=None, search_date=None):
        """Search trips by destination and/or date"""
        if destination and search_date:
            query = """
                SELECT * FROM trips 
                WHERE (destination LIKE ? OR departure_location LIKE ?)
                AND DATE(departure_time) = DATE(?)
                ORDER BY departure_time
            """
            search_term = f"%{destination}%"
            self.db.execute(query, (search_term, search_term, search_date))
        elif destination:
            return self.search_trips_by_destination(destination)
        elif search_date:
            return self.search_trips_by_date(search_date)
        else:
            # Return all trips if no search criteria
            query = "SELECT * FROM trips ORDER BY departure_time DESC"
            self.db.execute(query)
        return self.db.fetchall()
    
    def get_all_trips(self):
        """Get all trips ordered by departure time"""
        query = "SELECT * FROM trips ORDER BY departure_time DESC"
        self.db.execute(query)
        return self.db.fetchall()
    
    def get_employee_next_trip(self, employee_name):
        """Get the next upcoming trip for an employee"""
        query = """
            SELECT * FROM trips 
            WHERE employee_name = ? 
            AND datetime(departure_time) >= datetime('now')
            ORDER BY departure_time ASC
            LIMIT 1
        """
        self.db.execute(query, (employee_name,))
        return self.db.fetchone()
    
    def get_employee_upcoming_trips(self, employee_name):
        """Get all upcoming trips for an employee (excluding the next one)"""
        query = """
            SELECT * FROM trips 
            WHERE employee_name = ? 
            AND datetime(departure_time) >= datetime('now')
            ORDER BY departure_time ASC
        """
        self.db.execute(query, (employee_name,))
        all_upcoming = self.db.fetchall()
        # Return all except the first one (which is the "next" trip)
        return all_upcoming[1:] if len(all_upcoming) > 1 else []
    
    def get_employee_past_trips(self, employee_name):
        """Get all past trips for an employee"""
        query = """
            SELECT * FROM trips 
            WHERE employee_name = ? 
            AND datetime(departure_time) < datetime('now')
            ORDER BY departure_time DESC
        """
        self.db.execute(query, (employee_name,))
        return self.db.fetchall()
    
    def get_employee_all_trips(self, employee_name):
        """Get all trips for an employee"""
        query = """
            SELECT * FROM trips 
            WHERE employee_name = ?
            ORDER BY departure_time DESC
        """
        self.db.execute(query, (employee_name,))
        return self.db.fetchall()
