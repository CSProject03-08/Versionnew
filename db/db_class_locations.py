

class Locations:
    def __init__(self, db):
        self.db = db
    
    def add_location(self, location_name, location_ID, longitude, latitude, capacity):
        query = "INSERT INTO locations (name, location_ID, longitude, latitude, capacity) VALUES (?, ?, ?, ?, ?)"
        self.db.execute(query, (location_name, location_ID, longitude, latitude, capacity))
        self.db.commit()    

    def get_location(self, location_id):
        query = "SELECT * FROM locations WHERE id = ?"
        self.db.execute(query, (location_id,))
        return self.db.fetchone()
    
    def update_location(self, location_id, name=None, address=None, capacity=None):
        fields = []
        values = []
        if name:
            fields.append("name = ?")
            values.append(name)
        if address:
            fields.append("address = ?")
            values.append(address)
        if capacity:
            fields.append("capacity = ?")
            values.append(capacity)
        values.append(location_id)
        query = f"UPDATE locations SET {', '.join(fields)} WHERE id = ?"
        self.db.execute(query, tuple(values))
        self.db.commit()

    def delete_location(self, location_id):
        query = "DELETE FROM locations WHERE id = ?"
        self.db.execute(query, (location_id,))
        self.db.commit()

