import sqlite3
import streamlit as st 
import pandas as pd   

from .db_connection import Database
from .db_class_users import Users, Admins, Managers, Employees
from .db_class_events import Events

db = Database()
db.connect()

# Initialize user classes (they use set_db pattern)
admins_db = Admins()
admins_db.set_db(db)
managers_db = Managers()
managers_db.set_db(db)
employees_db = Employees()
employees_db.set_db(db)

# Initialize events class (passes db to constructor)
events_db = Events(db)

def close():
    db.close()

__all__ = [
    "db",
    "users_db",
    "admins_db",
    "managers_db",
    "employees_db",
    "events_db",
    "close"
]