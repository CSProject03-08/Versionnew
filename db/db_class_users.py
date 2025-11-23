
"""Module for managing Users (Admin, Manager, Employee) and in the database."""


class Users:
    def __init__(self):
        """User_ID, Username, First_Name, Last_Name, Password, Role"""
        self.user = "User"
        self.user_id = "User ID"
        self.username = "Username"
        self.first_name = "First Name"
        self.last_name = "Last Name"
        self.password = "Password"
        self.role = "Role"
        self.db = None  

    def set_db(self, db):
        self.db = db

    def create_user(self, username, password, role):
        query = "INSERT INTO users (username, password, role) VALUES (?, ?, ?)"
        self.db.execute(query, (username, password, role))
        self.db.commit()    

    def get_user(self, user_id):
        query = "SELECT * FROM users WHERE id = ?"
        self.db.execute(query, (user_id,))
        return self.db.fetchone()

    def update_user(self, user_id, username=None, password=None, role=None):
        fields = []
        values = []
        if username:
            fields.append("username = ?")
            values.append(username)
        if password:
            fields.append("password = ?")
            values.append(password)
        if role:
            fields.append("role = ?")
            values.append(role)
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        self.db.execute(query, tuple(values))
        self.db.commit()


class Admins(Users):
    """Admin subclass that inherits from Users"""
    
    def __init__(self):
        super().__init__()  # Call parent __init__
        self.role = "Admin"  # Override role
    
    def delete_user(self, user_id):
        """Admin-specific method to delete users"""
        query = "DELETE FROM users WHERE id = ?"
        self.db.execute(query, (user_id,))
        self.db.commit()
    
    def get_all_users(self):
        """Admin-specific method to view all users"""
        query = "SELECT * FROM users"
        self.db.execute(query)
        return self.db.fetchall()

class Managers(Users):
    """Manager subclass that inherits from Users"""
    
    def __init__(self):
        super().__init__()  # Call parent __init__
        self.role = "Manager"  # Override role
    
    def get_team_members(self, team_id):
        """Manager-specific method to view team members"""
        query = "SELECT * FROM users WHERE team_id = ?"
        self.db.execute(query, (team_id,))
        return self.db.fetchall()
    
class Employees(Users):
    """Employee subclass that inherits from Users"""
    
    def __init__(self):
        super().__init__()  # Call parent __init__
        self.role = "Employee"  # Override role
    
    def view_profile(self, user_id):
        """Employee-specific method to view own profile"""
        return self.get_user(user_id)