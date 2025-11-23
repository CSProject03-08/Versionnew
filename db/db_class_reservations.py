"""Module for managing Events and Trips in the database."""

"Defines class: Event and subclass Trip"


class Reservations:

    def __init__(self, db):
        self.db = db

    def create_reservation(self, event_id, user_id, reservation_date):
        query = "INSERT INTO reservations (event_id, user_id, reservation_date) VALUES (?, ?, ?)"
        self.db.execute(query, (event_id, user_id, reservation_date))
        self.db.commit()

    def get_reservation(self, reservation_id):
        query = "SELECT * FROM reservations WHERE id = ?"
        self.db.execute(query, (reservation_id,))
        return self.db.fetchone()

    def update_reservation(self, reservation_id, event_id=None, user_id=None, reservation_date=None):
        fields = []
        values = []
        if event_id:
            fields.append("event_id = ?")
            values.append(event_id)
        if user_id:
            fields.append("user_id = ?")
            values.append(user_id)
        if reservation_date:
            fields.append("reservation_date = ?")
            values.append(reservation_date)
        values.append(reservation_id)
        query = f"UPDATE reservations SET {', '.join(fields)} WHERE id = ?"
        self.db.execute(query, tuple(values))
        self.db.commit()

    def delete_reservation(self, reservation_id):
        query = "DELETE FROM reservations WHERE id = ?"
        self.db.execute(query, (reservation_id,))
        self.db.commit()

class Tickets (Reservations):
    """Ticket subclass that inherits from Reservations"""
        
    def __init__(self, db):
        super().__init__(db)  # Call parent __init__
        self.reservation_type = "Ticket"  # Additional attribute for Tickets

    def issue_ticket(self, event_id, user_id, seat_number):
        """Ticket-specific method to issue a ticket"""
        query = "INSERT INTO tickets (event_id, user_id, seat_number) VALUES (?, ?, ?)"
        self.db.execute(query, (event_id, user_id, seat_number))
        self.db.commit()