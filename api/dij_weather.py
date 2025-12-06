# api_weather.py

import time
from datetime import datetime, date
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def robust_get(url, params=None, retries=3, timeout=20):
    """Einfache GET-Anfrage mit Retry-Logik."""
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
    """Suche Ort über Open-Meteo-Geocoding und wähle – wenn möglich – eine CH-Lokation."""
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

    ch = [r for r in results if r.get("country_code") == "CH"]
    if not ch:
        return None

    loc = ch[0]
    return {
        "name": loc.get("name"),
        "admin1": loc.get("admin1"),
        "lat": loc.get("latitude"),
        "lon": loc.get("longitude"),
    }


def get_forecast(lat: float, lon: float):
    """Hole stündliche Vorhersage für Temperatur und Niederschlagswahrscheinlichkeit."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability",
        "current_weather": True,
        "timezone": "Europe/Zurich",
    }
    return robust_get(FORECAST_URL, params=params)


def build_hourly_df(forecast: dict) -> pd.DataFrame:
    """Baue DataFrame mit stündlicher Temperatur und Niederschlagswahrscheinlichkeit."""
    hourly = forecast.get("hourly", {})

    df = pd.DataFrame(
        {
            "time": hourly.get("time", []),
            "temperature": hourly.get("temperature_2m", []),
            "precip_prob": hourly.get("precipitation_probability", []),
        }
    )

    if df.empty:
        return df

    df["time"] = pd.to_datetime(df["time"])
    df.set_index("time", inplace=True)
    return df


def _to_date(d) -> date:
    """Konvertiere flexible Datums-Formate robust in date."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    return datetime.fromisoformat(str(d)).date()


def show_trip_weather(destination: str, start_date, end_date) -> None:
    """
    Zeigt eine kombinierte Grafik für einen Trip:
    - stündliche Temperatur (Linie)
    - Niederschlagswahrscheinlichkeit (Balken, zweite y-Achse)
    """

    start = _to_date(start_date)
    end = _to_date(end_date)

    try:
        loc = search_location(destination)
    except RuntimeError as e:
        st.error(str(e))
        return

    if loc is None:
        st.error(f"Ort '{destination}' wurde nicht gefunden.")
        return

    try:
        forecast = get_forecast(lat=loc["lat"], lon=loc["lon"])
    except RuntimeError as e:
        st.error(str(e))
        return

    df = build_hourly_df(forecast)
    if df.empty:
        st.warning("Keine Wetterdaten verfügbar.")
        return

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    df = df.loc[(df.index >= start_dt) & (df.index <= end_dt)]

    if df.empty:
        st.warning("Im gewählten Zeitraum liegen keine Daten vor.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["temperature"],
            mode="lines",
            name="Temperatur [°C]",
        )
    )

    if "precip_prob" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["precip_prob"],
                name="Niederschlagswahrscheinlichkeit [%]",
                opacity=0.3,
                yaxis="y2",
            )
        )

    fig.update_layout(
        title=f"Wetter für Trip nach {loc['name']} ({loc.get('admin1', '')})",
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
        margin=dict(l=40, r=40, t=40, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Standort: {loc['name']}, {loc.get('admin1', '')} – Datenquelle: open-meteo.com"
    )