import pyodbc
import streamlit as st

SERVER_NAME = st.secrets["azure_db"]["SERVER_NAME"]
DATABASE_NAME = st.secrets["azure_db"]["DATABASE_NAME"]
USERNAME = st.secrets["azure_db"]["USERNAME"]
PASSWORD = st.secrets["azure_db"]["PASSWORD"]

CONNECTION_STRING = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    f'SERVER={SERVER_NAME};'
    f'DATABASE={DATABASE_NAME};'
    f'UID={USERNAME};'
    f'PWD={PASSWORD};'
    'Encrypt=yes;'  
    'TrustServerCertificate=no;'
)

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
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO expenses_user_data (user_id, dest_city, duration_days, distance_km, total_cost)
            VALUES (?, ?, ?, ?, ?)
        """, params=(user_id, dest_city, duration_days, distance_km, total_cost))
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
        # 6. Verbindung IMMER schließen
        if conn:
            try:
                conn.close()
            except Exception as e:
                print(f"Error while disconnecting from database: {e}")