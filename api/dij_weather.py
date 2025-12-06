# weather_widget_combined.py

import time
from datetime import datetime, date, timedelta

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def robust_get(url, params=None, retries=3, timeout=20):
    """Robuste GET-Anfrage mit Retry & Timeout."""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.5)
                continue
            raise RuntimeError("Timeout – bitte später erneut versuchen.")
        except Exception as e:
            raise RuntimeError(f"Netzwerkfehler: {e}")


def search_location(place_name: str):
    """Suche Ort über Open-Meteo-Geocoding, priorisiere Schweiz, falls vorhanden."""
    params = {
        "name": place_name,
        "count": 5,
        "language": "de",
        "format": "json",
    }
    data = robust_get(GEOCODING_URL, params=params)
    results = data.get("results", [])
    if not results:
        return None

    # Priorität: Schweiz, sonst erster Treffer
    ch = [r for r in results if r.get("country_code") == "CH"]
    loc = ch[0] if ch else results[0]

    return {
        "name": loc.get("name"),
        "admin1": loc.get("admin1"),
        "lat": loc.get("latitude"),
        "lon": loc.get("longitude"),
    }


def get_forecast(lat: float, lon: float):
    """Hole stündliche Vorhersage (Temperatur + Niederschlagswahrscheinlichkeit)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability",
        "timezone": "Europe/Zurich",
    }
    return robust_get(FORECAST_URL, params=params)


def build_hourly_df(forecast: dict) -> pd.DataFrame:
    """Baue DataFrame mit stündlichen Wetterdaten."""
    hourly = forecast.get("hourly", {})

    df = pd.DataFrame(
        {
            "time": pd.to_datetime(hourly.get("time", [])),
            "Temperatur [°C]": hourly.get("temperature_2m", []),
            "Niederschlagswahrscheinlichkeit [%]": hourly.get(
                "precipitation_probability", []
            ),
        }
    )

    if not df.empty:
        df.set_index("time", inplace=True)

    return df


def show_weather_widget(
    place_name: str = "St. Gallen",
    start: date | None = None,
    end: date | None = None,
):
    """
    Kombiniertes Widget:
    - stündliche Temperatur als Linie
    - Niederschlagswahrscheinlichkeit als blasse Balken (gleicher Zeitstrahl)
    """
    try:
        loc = search_location(place_name)
    except RuntimeError as e:
        st.error(str(e))
        return

    if loc is None:
        st.error(f"Ort '{place_name}' wurde nicht gefunden.")
        return

    try:
        forecast = get_forecast(loc["lat"], loc["lon"])
    except RuntimeError as e:
        st.error(str(e))
        return

    df = build_hourly_df(forecast)

    if df.empty:
        st.warning("Keine Wetterdaten verfügbar.")
        return

    # Zeitraumfilter setzen
    if start is not None or end is not None:
        if start is None:
            start = df.index[0].date()
        if end is None:
            end = df.index[-1].date()

        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        df = df.loc[(df.index >= start_dt) & (df.index <= end_dt)]

    if df.empty:
        st.warning("Im gewählten Zeitraum liegen keine Daten vor.")
        return

    fig = go.Figure()

    # Temperatur-Linie
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Temperatur [°C]"],
            mode="lines",
            name="Temperatur [°C]",
        )
    )

    # Niederschlagswahrscheinlichkeit als blasse Balken (zweite y-Achse)
    if "Niederschlagswahrscheinlichkeit [%]" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Niederschlagswahrscheinlichkeit [%]"],
                name="Niederschlagswahrscheinlichkeit [%]",
                opacity=0.3,
                yaxis="y2",
            )
        )

    fig.update_layout(
        title=f"Wetterverlauf für {loc['name']} ({loc.get('admin1', '')})",
        xaxis=dict(title="Zeit"),
        yaxis=dict(title="Temperatur [°C]"),
        yaxis2=dict(
            title="Niederschlagswahrscheinlichkeit [%]",
            overlaying="y",
            side="right",
            range=[0, 100],
        ),
        bargap=0,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Standort: {loc['name']}, {loc.get('admin1', '')} – Datenquelle: open-meteo.com"
    )