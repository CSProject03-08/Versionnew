# Verify creation
import streamlit as st
from db.db_connection import Database
from db.db_class_users import Users, Admins, Managers, Employees

db = Database()
db.connect()
admins = Admins()
admins.set_db(db)
managers = Managers()
managers.set_db(db)
employees = Employees()
employees.set_db(db)
admins.create_user("Anna", "Marty", "Tim")  #Inherited from Users
managers.create_user("Bob", "ManagerPass", "Manager")  # Inherited from Users
employees.create_user("Charlie", "EmployeePass", "Employee")  # Inherited from Users

# Verify retrieval
st.write("Users created successfully!")
st.write("Admin User:", admins.get_user(1))
st.write("Manager User:", managers.get_user(2))
st.write("Employee User:", employees.get_user(3))

# Verify update
admins.update_user(1, password="NewAdminPass")  #Inherited from Users
managers.update_user(2, password="NewManagerPass")  #Inherited from Users
employees.update_user(3, password="NewEmployeePass")

st.write("Users updated successfully!")
st.write("Admin User:", admins.get_user(1))
st.write("Manager User:", managers.get_user(2))
st.write("Employee User:", employees.get_user(3))

# Verify deletion
admins.delete_user(3)  #Inherited from Users
st.write("Employee deleted successfully!")
st.write("Remaining Users:")
st.write("Admin User:", admins.get_user(1))
st.write("Manager User:", managers.get_user(2))
# employees.get_user(3) should return None

# Verify get_all_users
st.write("All Users:")
all_users = admins.get_all_users()
for user in all_users:
    st.write(user)

# Verify get_team_members
st.write("Team Members for team_id 1:")
team_members = managers.get_team_members(1)
for member in team_members:
    st.write(member)


#Inherited from Users
st.write("Admin User:", admins.get_user(1))
st.write("Manager User:", managers.get_user(2))
st.write("Employee User:", employees.get_user(3))
db.close()


