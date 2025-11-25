import sqlite3

DB_PATH = "ml/expenses_user_data.db"

def insert_expense_for_training(dest_city, distance_km, duration_days, total_cost, user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO expenses_user_data (user_id, dest_city, duration_days, distance_km, total_cost)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, dest_city, duration_days, distance_km, total_cost))

    conn.commit()
    conn.close()