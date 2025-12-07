"""dij_weather.py contains the weather visualization for the employee."""

import time
from datetime import datetime, date
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def robust_get(url, params=None, retries=3, timeout=20):
    """
    Simple get request with retry logic.
    
    Args:
        url (str): the url from the weather api
        params (dict): params for
        retries (int): number of retrials
        timeout (int): time until the search triggers a timeout
        
    Returns:
        r as json script of the request"""
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
    """
    Search for a place using open-meteo geocoding and choose a Swiss location if possible.
    
    Args:
        place_name (str): the destination of the trip
        
    Returns:
        dict with the name"""
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
    """Gets the weather forecast from open-meteo.com."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability",
        "current_weather": True,
        "timezone": "Europe/Zurich",
    }
    return robust_get(FORECAST_URL, params=params)


def build_hourly_df(forecast: dict) -> pd.DataFrame:
    """builds a dataframe from the hourly forecast data."""
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
    """converts various date inputs to a date object."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    return datetime.fromisoformat(str(d)).date()


def show_trip_weather(destination: str, start_date, end_date) -> None:
    """
    shows combined weather data for a trip, temperature and rain chances.
    Args:
        destination (str): the trip destination
        start_date (date): the trip start date
        end_date (date): the trip end date
    Returns:    
        None
    """

    start = _to_date(start_date)
    end = _to_date(end_date)

    try:
        loc = search_location(destination)
    except RuntimeError as e:
        st.error(str(e))
        return

    if loc is None:
        st.error(f"Place '{destination}' wasn't found.")
        return

    try:
        forecast = get_forecast(lat=loc["lat"], lon=loc["lon"])
    except RuntimeError as e:
        st.error(str(e))
        return

    df = build_hourly_df(forecast)
    if df.empty:
        st.warning("No data available.")
        return

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    df = df.loc[(df.index >= start_dt) & (df.index <= end_dt)]

    if df.empty:
        st.warning("No available data in this time.")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["temperature"],
            mode="lines",
            name="Temperature [°C]",
        )
    )

    if "precip_prob" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["precip_prob"],
                name="Chances of rain [%]",
                opacity=0.3,
                yaxis="y2",
            )
        )

    fig.update_layout(
        title=f"Weather for trip to {loc['name']} ({loc.get('admin1', '')})",
        xaxis=dict(title="Time"),
        yaxis=dict(title="Temperature [°C]"),
        yaxis2=dict(
            title="Chances of rain [%]",
            overlaying="y",
            side="right",
            range=[0, 100],
        ),
        bargap=0,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=40, r=40, t=40, b=40),
    )

    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"Location: {loc['name']}, {loc.get('admin1', '')} – Source: open-meteo.com"
    )