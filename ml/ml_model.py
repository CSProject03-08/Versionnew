"""
This module handles the connection to the Azure SQL database,
and the training and loading of the machine learning model that predicts total trip costs.

It expects a table called "expenses_user_data" that stores trip records with at least the following fields
- dest_city
- distance_km
- duration_days
- total_cost

The model is trained on these data and saved as "model.pkl" in the same directory as this file.
If no model exists yet, the module can bootstrap from a local CSV file called "seed_trips.csv".

In addition, helper functions are provided to classify Swiss cities into three cost tiers.
Cities that are not explicitly listed in any tier are treated as Tier 3 by default.
"""
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

# Tier 1 Cities: Swiss cities considered most expensive for seed data generation
TIER_1_CITIES = {
    "Zurich", "Geneva", "Basel", "Lausanne", "Zermatt", "St. Moritz",
    "Davos", "Klosters", "Verbier", "Gstaad", "Andermatt", "Grindelwald",
    "Wengen", "Mürren", "Saas-Fee", "Arosa", "Lenzerheide", "Flims", "Laax",
    "Engelberg", "Crans-Montana", "Montreux", "Lucerne", "Ascona", "Zug"
}

# Tier 2 Cities: Swiss cities considered moderately expensive for seed data generation
TIER_2_CITIES = {
    "Bern", "Winterthur", "St. Gallen", "Biel", "Schaffhausen",
    "Chur", "Thun", "Neuchâtel", "Fribourg", "Sion", "Brig", "Bellinzona",
    "Interlaken", "Kloten", "Lugano", "Locarno",
}

# Tier 3 Cities: Swiss cities considered least expensive for seed data generation
TIER_3_CITIES = {
    "Solothurn", "Olten", "Rapperswil", "Uster", "Baden", "Wil", "Arbon",
    "Romanshorn", "Spiez", "Steffisburg", "Villars-sur-Glâne", "Pfäffikon", "Wetzikon"
}

def get_tier(city: str) -> str:
    """Determines the cost tier of a given city.

    The function checks whether the city appears in one of the predefined
    tier sets and returns the corresponding tier label. If a city does not
    appear in any of the sets, it is treated as Tier 3 by default.

    This behaviour can be used as a fallback for cities that do not appear
    in the seed data, i.e. they are treated as "cheaper" Tier 3 locations.

    Args:
        city: Name of the city.

    Returns:
        The tier label "T1", "T2" or "T3".
    """
    if city in TIER_1_CITIES:
        return "T1"
    if city in TIER_2_CITIES:
        return "T2"
    if city in TIER_3_CITIES:
        return "T3"
    # Fallback: any unknown city is treated as Tier 3
    return "T3"

def connect():
    """Connects to Azure SQL-database.
    
    Returns:
        pyodbc.Connection"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # show the error
        st.error(f"Connection error: {sqlstate}")
        return None

def _ensure_table(conn: pyodbc.Connection):
    """Ensures that the training table exists in the Azure SQL database.
    The function assumes that the connection has already been opened. 
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

def _make_pipeline():
    """
    Build the sklearn pipeline:
    - OneHotEncode dest_city
    - pass through distance_km and duration_days as numeric
    - LinearRegression model
    """
    categorical_cols = ["tier", "dest_city"]
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

# initial train of model with sample data
def initial_train_from_csv(csv_path: str):
    """
    Seeds the database from a CSV (seed_trips.csv) and trains the initial model.

    CSV must contain at least:
      - dest_city
      - duration_days
      - distance_km
      - total_cost
    All rows are inserted into the training table with a fixed user_id ("seed") and date ("2025-12-07").
    
    Args:
        csv_path: Path to the CSV file containing seed data.
    
    Returns:
        The mean absolute error (MAE) on a hold-out validation set if there are enough samples; otherwise None.
    """
    df = pd.read_csv(csv_path)

    needed = {"dest_city", "duration_days", "distance_km", "total_cost"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    # seed rows into DB, tagged as 'seed' for filtering later if needed
    df_to_db = df.assign(user_id="seed", date="2025-12-07")[
        ["user_id", "date", "dest_city", "duration_days", "distance_km", "total_cost"]
    ]

    conn = connect()
    _ensure_table(conn)
    if conn is None:
        return None
    
    df_to_db.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    conn.close()

    # train + save
    return retrain_model()

# subsequent training model with user + seed data
def retrain_model():
    """
    Trains or retrains the model on all rows in the table.

    All rows from the training table are loaded and used to fit the model.
    If there are at least 8 samples, a hold-out validation set is used to
    compute the mean absolute error (MAE). Otherwise, the model is trained
    on the full dataset without validation.

    The trained pipeline is saved to model.pkl.

    Returns:
        The MAE on the validation set if there are enough samples; otherwise None.
    """
    conn = connect()
    _ensure_table(conn)
    if conn is None:
        return None

    df = pd.read_sql_query(
        f"SELECT dest_city, distance_km, duration_days, total_cost FROM {TABLE_NAME}",
        conn,
    )
    conn.close()

    if df.empty:
        return None 

    df["tier"] = df["dest_city"].apply(get_tier)

    X = df[["tier", "dest_city", "distance_km", "duration_days"]]
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
    Loads the trained model with fallback to seed-based training.

    - If model.pkl is missing, the model tries to train from seed_trips.csv
    - If unpickling model.pkl fails, the function tries to rebuild the model from seed data.
    
    Returns:
        Trained model, or None if loading fails.
    """
    csv_path = BASE_DIR / "seed_trips.csv"

    def _train_from_seed_if_possible():
        if csv_path.exists():
            try:
                print("Rebuilding ML model from seed_trips.csv...")
                initial_train_from_csv(str(csv_path))
            except Exception as e:
                print(f"Rebuild from seed_trips.csv failed: {e}")

    # 1) No model.pkl yet → try to build it from seed data
    if not MODEL_PATH.exists():
        _train_from_seed_if_possible()

    # 2) Try to load existing model.pkl
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        # Most likely: incompatible pickle from a different environment
        print(f"Could not load model.pkl ({e}). Trying to rebuild from seed.")
        _train_from_seed_if_possible()

        # Try one more time after rebuilding
        try:
            with open(MODEL_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e2:
            print(f"Failed to load model.pkl even after rebuild: {e2}")
            return None
