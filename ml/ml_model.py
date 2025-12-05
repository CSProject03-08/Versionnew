import pyodbc
import pickle
from pathlib import Path
import streamlit as st

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression  # multiple linear regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

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

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "model.pkl"
TABLE_NAME = "expenses_user_data"

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

def _make_pipeline():
    """
    Build the sklearn pipeline:
    - OneHotEncode dest_city
    - pass through distance_km and duration_days as numeric
    - LinearRegression model
    """
    categorical_cols = ["dest_city"]
    numeric_cols = ["distance_km", "duration_days"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
            ("num", "passthrough", numeric_cols),
        ]
    )

    pipe = Pipeline(steps=[
        ("pre", preprocessor),
        ("model", LinearRegression()),
    ])
    return pipe


def _ensure_table(conn: pyodbc.Connection):
    """
    Stellt sicher, dass die Trainings-Tabelle (TABLE_NAME) in der Azure SQL DB existiert.
    Die Funktion geht davon aus, dass 'conn' eine bereits geöffnete pyodbc-Verbindung ist.
    """
    if conn is None:
        print("No connection to database possible")
        return

    try:
        c = conn.cursor()

        sql_query = f"""
            IF OBJECT_ID('{TABLE_NAME}', 'U') IS NULL
            BEGIN
                CREATE TABLE {TABLE_NAME} (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    user_id NVARCHAR(50),
                    date NVARCHAR(50),
                    dest_city NVARCHAR(100),
                    duration_days REAL,
                    distance_km REAL,
                    total_cost REAL
                );
            END
        """
        c.execute(sql_query)
        conn.commit()
        print(f"INFO: Tabelle '{TABLE_NAME}' ist verifiziert oder wurde erfolgreich erstellt.")

    except pyodbc.Error as e:
        print(f"FEHLER: Konnte Tabelle '{TABLE_NAME}' nicht erstellen oder verifizieren: {e}")
        # rollback if error occures
        conn.rollback()


# initial train of model with sample data
def initial_train_from_csv(csv_path: str):
    """
    Seed the DB from a CSV (e.g. seed_trips.csv) and train the initial model.

    CSV must contain at least:
      - dest_city
      - duration_days
      - distance_km
      - total_cost
    """
    df = pd.read_csv(csv_path)

    # minimal schema check
    needed = {"dest_city", "duration_days", "distance_km", "total_cost"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    # seed rows into DB, tagged as 'seed' so you can filter later if needed
    df_to_db = df.assign(user_id="seed", date="2025-01-01")[
        ["user_id", "date", "dest_city", "duration_days", "distance_km", "total_cost"]
    ]

    conn = connect()
    _ensure_table(conn)
    df_to_db.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    conn.close()

    # train + save
    return retrain_model()


# subsequent training model with user + seed data
def retrain_model():
    """
    Train (or retrain) the model on all rows in the training table.
    """
    conn = connect()
    _ensure_table(conn)
    df = pd.read_sql_query(
        f"SELECT dest_city, distance_km, duration_days, total_cost FROM {TABLE_NAME}",
        conn
    )
    conn.close()

    if df.empty:
        return None  # nothing to train yet

    X = df[["dest_city", "distance_km", "duration_days"]]
    y = df["total_cost"]

    pipe = _make_pipeline()

    # Hold-out evaluation if we have enough samples
    if len(df) >= 8:
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        pipe.fit(X_tr, y_tr)
        mae = mean_absolute_error(y_te, pipe.predict(X_te))
    else:
        pipe.fit(X, y)
        mae = None

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipe, f)

    return mae


def load_model():
    """
    Load the trained model from disk.

    - If model.pkl is missing, try to train from seed_trips.csv once.
    - If unpickling fails (environment mismatch), try to rebuild once.
    - If everything fails, return None so the app can show a friendly message.
    """
    csv_path = BASE_DIR / "seed_trips.csv"

    def _train_from_seed_if_possible():
        if csv_path.exists():
            try:
                print("🔁 Rebuilding ML model from seed_trips.csv...")
                initial_train_from_csv(str(csv_path))
            except Exception as e:
                print(f"⚠️ Rebuild from seed_trips.csv failed: {e}")

    # 1) No model.pkl yet → try to build it from seed data
    if not MODEL_PATH.exists():
        _train_from_seed_if_possible()

    # Still no model.pkl? Then we simply have no model.
    if not MODEL_PATH.exists():
        return None

    # 2) Try to load existing model.pkl
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        # Most likely: incompatible pickle from a different environment
        print(f"⚠️ Could not load model.pkl ({e}). Trying to rebuild from seed.")
        _train_from_seed_if_possible()

        # Try one more time after rebuilding
        try:
            with open(MODEL_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e2:
            print(f"❌ Failed to load model.pkl even after rebuild: {e2}")
            return None
