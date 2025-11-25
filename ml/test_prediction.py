from ml.ml_model import load_model
from geopy.distance import geodesic
import pandas as pd

# Load the trained model
model = load_model()
if model is None:
    print("❌ No trained model found. Please run ml_app.py first to train it.")
    exit()

# Example input: 3-day business trip from St. Gallen to Geneva
dest_city = "Geneva"
duration_days = 3.0

# Compute distance (same as during training)
distance_km = geodesic(COORDS[ORIGIN], COORDS[dest_city]).km

# Build a small DataFrame for prediction
X_new = pd.DataFrame([{
    "dest_city": dest_city,
    "distance_km": distance_km,
    "duration_days": duration_days
}])

# Predict the total cost
predicted_cost = model.predict(X_new)[0]
print(f"🧳 Predicted total cost for {duration_days}-day trip to {dest_city}: CHF {predicted_cost:.2f}")
