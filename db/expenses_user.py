import pyodbc
import streamlit as st
from utils import load_secrets
from sqlalchemy import create_engine
import urllib

CONNECTION_STRING = load_secrets()
connect_uri = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(CONNECTION_STRING)
engine = create_engine(connect_uri, fast_executemany=True)

def connect():
    """Connects to Azure SQL-database"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # show the error
        st.error(f"Connection error: {sqlstate}")
        return None

def insert_expense_for_training(dest_city, distance_km, duration_days, total_cost, user_id):
    """Inserts an expense report into the expenses_user_data table.
    Args:
        dest_city (str): Destination city of the trip.
        distance_km (float): Distance traveled in kilometers.
        duration_days (int): Duration of the trip in days.
        total_cost (float): Total cost of the trip.
        user_id (int): ID of the user submitting the expense report.
    Returns:
        bool: True if the insertion was successful, False otherwise.
    """
    
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO expenses_user_data (user_id, dest_city, duration_days, distance_km, total_cost)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, dest_city, duration_days, distance_km, total_cost))
        conn.commit()
        st.success("Successful saved in database")
        return True

    except pyodbc.Error as e:
        if conn:
            conn.rollback()
        
        st.error(f"Database error: {e}")
        print(f"SQL Execution Error: {e}") 
        return False

    except Exception as e:
        if conn:
            conn.rollback()
            
        st.error(f"An unexpected error has appeared: {e}")
        print(f"Unexpected Error: {e}")
        return False

    finally:
        # always close the connection
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Error while disconnecting from database: {e}")
