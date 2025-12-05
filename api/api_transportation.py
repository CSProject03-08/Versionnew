# api/api_transportation.py

import streamlit as st
import googlemaps
from datetime import datetime, timedelta
import polyline
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# Globaler Client, initialisiert auf None, um ImportError zu vermeiden.
# Die Zuweisung GOOGLE_API_KEY = st.secrets[...] wurde entfernt!
gmaps = None

# ---------- Helper ----------

def get_route(origin: str, destination: str, mode: str = "driving"):
    """Fetch a single route (first alternative) from Google Directions API."""
    global gmaps

    if gmaps is None:
        # Hier sollte gmaps eigentlich schon initialisiert sein,
        # aber wir verhindern den Absturz im Helper.
        # WICHTIG: Wenn diese Funktion direkt aufgerufen wird, ohne
        # vorher transportation_managerview auszuführen, fehlt der Client.
        st.error("Google Maps client is not initialised. Call transportation_managerview first.")
        return None

    try:
        directions = gmaps.directions(
            origin,
            destination,
            mode=mode,
            departure_time="now",
            language="en",
        )
        if not directions:
            return None
        return directions[0]
    except Exception as e:
        st.error(f"Google Maps error ({mode}): {e}")
        return None


def calculate_costs_auto(dist_km: float) -> dict:
    """
    Simple car cost model:
    - allowance per km: CHF 0.75
    """
    allowance_per_km = 0.75
    total = dist_km * allowance_per_km
    return {
        "comp": allowance_per_km,   # CHF per km
        "total": total              # total CHF
    }


def calculate_costs_ov(dist_km: float) -> dict:
    """
    Simple public transport cost model (fallback, wenn keine echte Fare-API verwendet wird):
    - base price: CHF 2.80
    - price per km: CHF 0.31
    """
    base_price = 2.80
    price_per_km = 0.31
    ticket = base_price + dist_km * price_per_km
    return {
        "ticket": ticket,
        "total": ticket
    }


def get_ticket_price_opendata(
    start: str,
    dest: str,
    date_obj=None,
    time_obj=None,
    default_price: float = 30.0
) -> float:
    """
    Versucht, über transport.opendata.ch eine reale Fare zu holen.
    Falls Fehler → default_price.
    """
    if date_obj is None:
        date_obj = datetime.now().date()
    if time_obj is None:
        time_obj = datetime.now().time()

    url = "https://transport.opendata.ch/v1/connections"
    params = {
        "from": start,
        "to": dest,
        "date": date_obj.strftime("%Y-%m-%d"),
        "time": time_obj.strftime("%H:%M"),
        "limit": 1
    }

    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()

        connections = data.get("connections")
        if not connections:
            return default_price

        conn0 = connections[0]
        fare = conn0.get("fare")
        if fare is None:
            return default_price

        return float(fare)
    except Exception:
        # Fallback auf default_price, wenn irgendetwas schief geht
        return default_price


def get_transit_transfers_full(route_transit: dict):
    """
    Extrahiert grob die wichtigsten Umstiege aus einer Transit-Route.
    Gibt eine Liste von Strings zurück.
    """
    if not route_transit:
        return []

    transfers = []
    legs = route_transit.get("legs", [])
    if not legs:
        return transfers

    leg0 = legs[0]
    steps = leg0.get("steps", [])

    # Startpunkt
    transit_steps = [s for s in steps if s.get("travel_mode") == "TRANSIT"]
    if not transit_steps:
        return transfers

    first = transit_steps[0]
    dep_stop = first["transit_details"]["departure_stop"]["name"]
    dep_time = first["transit_details"]["departure_time"]["text"]
    transfers.append(f"Start: {dep_stop} - {dep_time}")

    # Umstiege
    prev_line = None
    prev_arr_stop = None
    for step in transit_steps:
        details = step["transit_details"]
        line_name = details.get("line", {}).get("short_name") or details.get("line", {}).get("name")
        arr_stop = details["arrival_stop"]["name"]
        arr_time = details["arrival_time"]["text"]

        if prev_line and prev_line != line_name:
            transfers.append(f"Umstieg: {prev_arr_stop} - {arr_time}")

        prev_line = line_name
        prev_arr_stop = arr_stop

    # Ziel
    last = transit_steps[-1]
    arr_stop = last["transit_details"]["arrival_stop"]["name"]
    arr_time = last["transit_details"]["arrival_time"]["text"]
    transfers.append(f"Ziel: {arr_stop} - {arr_time}")

    return transfers


def create_map(route: dict, origin: str, destination: str):
    """Erstellt eine Folium-Map für die angegebene Route."""
    if not route:
        return None

    leg0 = route["legs"][0]
    start_coords = [
        leg0["start_location"]["lat"],
        leg0["start_location"]["lng"],
    ]
    end_coords = [
        leg0["end_location"]["lat"],
        leg0["end_location"]["lng"],
    ]

    m = folium.Map(location=start_coords, zoom_start=12)

    folium.Marker(
        location=start_coords,
        popup=origin,
        icon=folium.Icon(color="green"),
    ).add_to(m)

    folium.Marker(
        location=end_coords,
        popup=destination,
        icon=folium.Icon(color="red"),
    ).add_to(m)

    # Route-Polyline
    if "overview_polyline" in route:
        points = polyline.decode(route["overview_polyline"]["points"])
        folium.PolyLine(points, color="blue", weight=5, opacity=0.7).add_to(m)

    return m


# ---------- Hauptfunktion für Manager-View ----------

def transportation_managerview(origin: str, destination: str, api_key: str | None = None):
    """
    Zeigt im Streamlit-UI einen Vergleich zwischen
    - Auto
    - öffentlichem Verkehr

    Diese Funktion ist so gebaut, dass du sie einfach aus create_trip_dropdown()
    mit origin, destination und api_key aufrufen kannst.
    """
    global gmaps

    # Validierung der Eingaben
    if not origin or not destination:
        st.info("Please enter origin and destination to see transport comparison.")
        return

    origin = origin.strip()
    destination = destination.strip()
    if not origin or not destination:
        st.info("Please enter origin and destination to see transport comparison.")
        return

    # API-Key Quelle (Jetzt defensiver Abruf von st.secrets)
    key = (api_key or "").strip()
    if not key:
        # st.secrets wird hier abgerufen, wo Streamlit aktiv ist
        key = st.session_state.get("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY", "")).strip()

    if not key:
        st.warning("Please provide a Google Maps API Key to calculate routes.")
        return
    
    # Initialisierung des Clients MUSS den lokal gefundenen Key verwenden
    if gmaps is None:
        try:
            # WICHTIG: Verwenden Sie den lokal gefundenen 'key'
            gmaps = googlemaps.Client(key=key) 
        except Exception as e:
            st.error(f"Could not initialise Google Maps client: {e}")
            return

    # Routen holen
    route_auto = get_route(origin, destination, mode="driving")
    route_transit = get_route(origin, destination, mode="transit")

    col1, col2 = st.columns(2)

    # ---------- Auto ----------
    with col1:
        st.subheader("Car")

        if route_auto:
            leg = route_auto["legs"][0]
            dist_km = leg["distance"]["value"] / 1000
            dur_min = leg["duration"]["value"] / 60

            cost_auto = calculate_costs_auto(dist_km)

            st.metric("Distance", f"{dist_km:.1f} km")
            st.metric("Duration", f"{dur_min:.0f} min")
            st.metric("Total costs", f"CHF {cost_auto['total']:.2f}")

            #m_auto = create_map(route_auto, origin, destination)
            #if m_auto is not None:
            #    st_folium(m_auto, width=700, height=400)
        else:
            st.info("No car route available or API error.")

    # ---------- Öffentlicher Verkehr ----------
    with col2:
        st.subheader("Public transport")

        if route_transit:
            leg = route_transit["legs"][0]
            dist_km = leg["distance"]["value"] / 1000
            dur_min = leg["duration"]["value"] / 60

            # einfache Kosten auf Distanz-Basis
            cost_ov = calculate_costs_ov(dist_km)

            # Optional: echte Fare via Opendata (falls verfügbar)
            # real_fare = get_ticket_price_opendata(origin, destination)
            # cost_ov["ticket"] = real_fare
            # cost_ov["total"] = real_fare

            st.metric("Distance", f"{dist_km:.1f} km")
            st.metric("Duration", f"{dur_min:.0f} min")
            st.metric("Total costs", f"CHF {cost_ov['total']:.2f}")

            #m_ov = create_map(route_transit, origin, destination)
            #if m_ov is not None:
            #    st_folium(m_ov, width=700, height=400)

            #transfers = get_transit_transfers_full(route_transit)
            #if transfers:
                #st.subheader("Stops and transfers")
                #for t in transfers:
                    #st.write(t)
        else:
            st.info("No public transport route available or API error.")

def show_transportation_details(method_transport, origin, destination, start_date, start_time):
    """
    Zeigt Transportation-Informationen für Car oder Public Transport.
    Wird von employee_listview() aufgerufen.
    """
        # ---- Styling für DataFrame kleiner & kompakter ----
    st.markdown("""
        <style>
        .stDataFrame tbody td {
            font-size: 13px !important;
            padding: 4px 6px !important;
        }
        .stDataFrame thead th {
            font-size: 14px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    # Ensure correct types
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    if isinstance(start_time, str):
        # unterstützt sowohl "HH:MM" als auch "HH:MM:SS"
        try:
            start_time = datetime.strptime(start_time, "%H:%M").time()
        except:
            start_time = datetime.strptime(start_time, "%H:%M:%S").time()
    col1, col2 = st.columns(2)

    # ---------------------------------------------------------
    # ------------- OPTION 0: CAR (GOOGLE DIRECTIONS) ---------
    # ---------------------------------------------------------
    if method_transport == 0:
        # Statt URL/requests direkt den gmaps Client verwenden (falls er global verfügbar ist)
        # Wenn gmaps in transportation_managerview initialisiert wurde, ist es hier verfügbar.
        # Alternativ: key neu abrufen und gmaps neu initialisieren.
        key = st.secrets.get("GOOGLE_API_KEY", "")
        if not key:
            st.warning("Cannot show map: API Key missing.")
            return

        # Sicherstellen, dass gmaps initialisiert ist
        global gmaps
        if gmaps is None:
            try:
                gmaps = googlemaps.Client(key=key)
            except Exception as e:
                st.error(f"Could not initialise Google Maps client for map: {e}")
                return
        
        # Daten über den Client holen (besser als requests.get)
        try:
            directions = gmaps.directions(
                origin,
                destination,
                mode="driving",
                language="en",
            )
        except Exception as e:
            st.warning(f"Could not retrieve driving route via Google Maps client: {e}")
            return

        if directions and directions[0]["legs"]:
            data = {"routes": directions} # Struktur an alten Code anpassen
            leg = data["routes"][0]["legs"][0]

            distance = leg["distance"]["text"]
            duration = leg["duration"]["text"]
            start_lat = leg["start_location"]["lat"]
            start_lng = leg["start_location"]["lng"]
            end_lat = leg["end_location"]["lat"]
            end_lng = leg["end_location"]["lng"]

            # ---- LEFT COLUMN ----
            with col1:
                st.subheader("Car details")
                st.write(f"**Distance:** {distance}")
                st.write(f"**Duration:** {duration}")

            # ---- RIGHT COLUMN (Map) ----
            with col2:
                m = folium.Map(
                    location=[(start_lat + end_lat) / 2, (start_lng + end_lng) / 2],
                    zoom_start=11
                )

                # Marker
                folium.Marker([start_lat, start_lng]).add_to(m)
                folium.Marker([end_lat, end_lng]).add_to(m)

                # ---- WICHTIG: echte Google-Route zeichnen ----
                if "overview_polyline" in data["routes"][0]:
                    poly = data["routes"][0]["overview_polyline"]["points"]
                    coords = polyline.decode(poly)
                    folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)
                else:
                    st.warning("No polyline available from Google Maps API.")

                st_folium(m, height=400, width=500)

        else:
            st.warning("Could not retrieve driving route via Google Maps.")

    # ---------------------------------------------------------
    # -------- OPTION 1: PUBLIC TRANSPORT (SBB + Google) -------
    # ---------------------------------------------------------
    elif method_transport == 1:
        # 1) Ziel: Verbindungen, die ca. 30 Minuten vor Eventbeginn ankommen
        #    → wir fragen die SBB-API mit einer Zeit, die 30 Min vor dem Event liegt
        event_dt = datetime.combine(start_date, start_time)
        query_dt = event_dt - timedelta(minutes=30)
        date_str = query_dt.strftime("%Y-%m-%d")
        time_str = query_dt.strftime("%H:%M")

        # ---- SBB OpenData: bis zu 3 Verbindungen holen ----
        sbb_url = "https://transport.opendata.ch/v1/connections"
        params = {
            "from": origin,
            "to": destination,
            "date": date_str,
            "time": time_str,
            "limit": 3,
        }

        try:
            r = requests.get(sbb_url, params=params, timeout=10)
            r.raise_for_status()
            sbb_data = r.json()
            connections = sbb_data.get("connections", [])
        except Exception as e:
            connections = []
            st.warning(f"Could not retrieve SBB connections: {e}")

        # ---- LINKE SPALTE: 3 Verbindungen in einer Tabelle ----
        with col1:
            st.subheader("Public Transport")

            if not connections:
                st.write("No connections found around the desired arrival time.")
            else:
                rows = []
                for i, conn in enumerate(connections[:3]):
                    dep = conn["from"]
                    arr = conn["to"]

                    dep_time_raw = dep.get("departure", "")
                    arr_time_raw = arr.get("arrival", "")

                    # Zeit formatieren
                    try:
                        dep_dt = datetime.strptime(dep_time_raw, "%Y-%m-%dT%H:%M:%S%z")
                        dep_time = dep_dt.strftime("%H:%M")
                    except:
                        dep_time = dep_time_raw

                    try:
                        arr_dt = datetime.strptime(arr_time_raw, "%Y-%m-%dT%H:%M:%S%z")
                        arr_time = arr_dt.strftime("%H:%M")
                    except:
                        arr_time = arr_time_raw

                    products = conn.get("products", [])
                    trains = ", ".join(products) if products else "-"

                    platform = (
                        dep.get("platform")
                        or dep.get("prognosis", {}).get("platform")
                        or "-"
                    )

                    rows.append({
                        "Departure": f"{dep_time} (Pl. {platform})",
                        "Arrival": arr_time,
                        "Train": trains
                    })

                # ✅ DataFrame nur mit den 3 gewünschten Spalten
                df = pd.DataFrame(rows)[["Departure", "Arrival", "Train"]]

                # Index als Connection 1, 2, 3
                df.index = [i + 1 for i in range(len(df))]
                df.index.name = "Connection"

                st.dataframe(df, use_container_width=True)
        
        # ---- RECHTE SPALTE: Karte über Google Directions (Transit) ----
        with col2:
            key = st.secrets.get("GOOGLE_API_KEY", "")
            if not key:
                st.warning("Cannot show map: API Key missing.")
                return

            g_url = "https://maps.googleapis.com/maps/api/directions/json"
            g_params = {
                "origin": origin,
                "destination": destination,
                "mode": "transit",
                "key": key, # Verwenden des lokal abgerufenen Keys
            }

            g_resp = requests.get(g_url, params=g_params)
            g_data = g_resp.json()

            if g_data.get("status") == "OK":
                leg = g_data["routes"][0]["legs"][0]

                start_lat = leg["start_location"]["lat"]
                start_lng = leg["start_location"]["lng"]
                end_lat = leg["end_location"]["lat"]
                end_lng = leg["end_location"]["lng"]

                # Karte mittig zwischen Start und Ziel
                m = folium.Map(
                    location=[(start_lat + end_lat) / 2, (start_lng + end_lng) / 2],
                    zoom_start=11,
                )

                folium.Marker(
                    [start_lat, start_lng],
                    tooltip="Start",
                    icon=folium.Icon(color="green"),
                ).add_to(m)
                folium.Marker(
                    [end_lat, end_lng],
                    tooltip="Destination",
                    icon=folium.Icon(color="red"),
                ).add_to(m)

                # Polyline der echten ÖV-Route von Google
                if "overview_polyline" in g_data["routes"][0]:
                    poly = g_data["routes"][0]["overview_polyline"]["points"]
                    coords = polyline.decode(poly)
                    folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)

                st_folium(m, height=210, width=500)
            else:
                st.warning("Could not retrieve transit route from Google Maps.")
    else:
        st.info("No transport method stored for this trip.")