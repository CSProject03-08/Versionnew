# api/api_transportation.py

import streamlit as st
import googlemaps
from datetime import datetime, timedelta
import polyline
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# global client, initialized on None to prevent ImportError
gmaps = None

# helper functions
def get_route(origin: str, destination: str, mode: str = "driving"):
    """
    Fetch a single route (first alternative) from Google Directions API.
    
    Args:
        origin (str): The origin of the trip
        destination (str): The destination of the trip
        mode (str): The travel method (car (driving) or public transport (transit))
        
    Returns:
        directions (dict): First trip details of the api.
    """
    global gmaps

    if gmaps is None: # gmaps should be initialized via transportation_managerview
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

    Args:
        dist_km (float): The travel distance in km.

    Returns:
        dict: Contains the allowance and the total cost for the trip by car.
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

    Args:
        dist_km (float): The travel distance in km.

    Returns:
        dict: Ticket price of the public transport for trip.
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
    Tries to get via transport.opendata.ch a real fare price.
    If it fails it retuns a default price.

    Args:
        start (str): The origin of the trip
        dest (str): The destination of the trip
        date_obj (None): Date of the trip (default None)
        time_obj (None): Time of the trip (default None)
        default_price (float): In case of failed trial the default price

    Returns:
        fare (float): The real fare of the public transport ticket via the api
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
        # fallback to default price in case it doesn't work
        return default_price


def get_transit_transfers_full(route_transit: dict):
    """
    Extracts the main points of transfer of the transit route.

    Args:
        route_transit (dict): The transit route as a dictionary

    Returns:
        transfers (list): A list with location and time of start, end and transfer points of the route
    """
    if not route_transit:
        return []

    transfers = []
    legs = route_transit.get("legs", [])
    if not legs:
        return transfers

    leg0 = legs[0]
    steps = leg0.get("steps", [])

    # strat point
    transit_steps = [s for s in steps if s.get("travel_mode") == "TRANSIT"]
    if not transit_steps:
        return transfers

    first = transit_steps[0]
    dep_stop = first["transit_details"]["departure_stop"]["name"]
    dep_time = first["transit_details"]["departure_time"]["text"]
    transfers.append(f"Start: {dep_stop} - {dep_time}")

    # transfer points
    prev_line = None
    prev_arr_stop = None
    for step in transit_steps:
        details = step["transit_details"]
        line_name = details.get("line", {}).get("short_name") or details.get("line", {}).get("name")
        arr_stop = details["arrival_stop"]["name"]
        arr_time = details["arrival_time"]["text"]

        if prev_line and prev_line != line_name:
            transfers.append(f"Transfer: {prev_arr_stop} - {arr_time}")

        prev_line = line_name
        prev_arr_stop = arr_stop

    # end point
    last = transit_steps[-1]
    arr_stop = last["transit_details"]["arrival_stop"]["name"]
    arr_time = last["transit_details"]["arrival_time"]["text"]
    transfers.append(f"Ziel: {arr_stop} - {arr_time}")

    return transfers


def create_map(route: dict, origin: str, destination: str):
    """
    Creates a folium map for the given route.

    Args:
        route (dict): The transit route as a dictionary
        origin (str): The origin of the trip
        destination (str): The destiantion of the trip

    Returns:
        m (folium.map): The folium map for the given route as a visualization
    """
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

    # green marker for the start location
    folium.Marker(
        location=start_coords,
        popup=origin,
        icon=folium.Icon(color="green"),
    ).add_to(m)

    # red marker for the end location
    folium.Marker(
        location=end_coords,
        popup=destination,
        icon=folium.Icon(color="red"),
    ).add_to(m)

    # blue line for the route
    if "overview_polyline" in route:
        points = polyline.decode(route["overview_polyline"]["points"])
        folium.PolyLine(points, color="blue", weight=5, opacity=0.7).add_to(m)

    return m


# main functions for the manager view
def transportation_managerview(origin: str, destination: str, api_key: str | None = None):
    """
    Shows in the streamlit UI a comparison between:
    - car
    - public transport
    This funciton is build in a way that it takes the inputs from the create_trip_dropdown()
    function (origin and destination) and the api key in order to compare the two alternatives.

    Args:
        origin (str): The origin of the trip
        destination (str): The destination of the trip
        api_key (str): The api key which is hidden in the st.secrets

    Returns:
        Two columns of the two alternatives but no return output
    """
    global gmaps

    # validation of inputs
    if not origin or not destination:
        st.info("Please enter origin and destination to see transport comparison.")
        return

    origin = origin.strip()
    destination = destination.strip()
    if not origin or not destination:
        st.info("Please enter origin and destination to see transport comparison.")
        return

    # api source called
    key = (api_key or "").strip()
    if not key:
        # st.secrets is called here
        key = st.session_state.get("GOOGLE_API_KEY", st.secrets.get("GOOGLE_API_KEY", "")).strip()

    if not key:
        st.warning("Please provide a Google Maps API Key to calculate routes.")
        return

    # initialization of the client. Has to use the local key
    if gmaps is None:
        try:
            # important: use the local key
            gmaps = googlemaps.Client(key=key) 
        except Exception as e:
            st.error(f"Could not initialise Google Maps client: {e}")
            return

    # getting route from helper function
    route_auto = get_route(origin, destination, mode="driving")
    route_transit = get_route(origin, destination, mode="transit")

    # devide in two columns
    col1, col2 = st.columns(2)

    # car coulumn
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

    # public transport column
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
    Shows transportation information and folium map for travel method for the employee.

    Args:
        method_transport (int): The transport method (0 = "car"; 1 = "public transport")
        origin (str): The origin of the trip
        destination (str): The destination of the trip
        start_date (date): The start date of the trip
        end_date (date): The end date of teh trip

    Returns:
        details of chosen transport method as visualization but no argument is returned
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
        # supports "HH:MM" as well as "HH:MM:SS"
        try:
            start_time = datetime.strptime(start_time, "%H:%M").time()
        except:
            start_time = datetime.strptime(start_time, "%H:%M:%S").time()
    col1, col2 = st.columns(2)

    # details for car
    if method_transport == 0:
        # instead of requesting the url we try to use the client gmaps if it exists
        # if transportation_managerview already got called the client will be initialized otherwise we call the key here and initialize the client a second time
        
        key = st.secrets.get("GOOGLE_API_KEY", "")
        if not key:
            st.warning("Cannot show map: API Key missing.")
            return

        # ensuring that gmaps is initialized
        global gmaps
        if gmaps is None:
            try:
                gmaps = googlemaps.Client(key=key)
            except Exception as e:
                st.error(f"Could not initialise Google Maps client for map: {e}")
                return
        
        # calling dates via client
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
            data = {"routes": directions} # adapting to ancient code structure
            leg = data["routes"][0]["legs"][0]

            distance = leg["distance"]["text"]
            duration = leg["duration"]["text"]
            start_lat = leg["start_location"]["lat"]
            start_lng = leg["start_location"]["lng"]
            end_lat = leg["end_location"]["lat"]
            end_lng = leg["end_location"]["lng"]

            # left column details
            with col1:
                st.subheader("Car details")
                st.write(f"**Distance:** {distance}")
                st.write(f"**Duration:** {duration}")

            # right column folium map
            with col2:
                m = folium.Map(
                    location=[(start_lat + end_lat) / 2, (start_lng + end_lng) / 2],
                    zoom_start=11
                )

                # marker for the map
                folium.Marker([start_lat, start_lng]).add_to(m)
                folium.Marker([end_lat, end_lng]).add_to(m)

                # polyline of the actual car route from google
                if "overview_polyline" in data["routes"][0]:
                    poly = data["routes"][0]["overview_polyline"]["points"]
                    coords = polyline.decode(poly)
                    folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)
                else:
                    st.warning("No polyline available from Google Maps API.")

                st_folium(m, height=400, width=500)

        else:
            st.warning("Could not retrieve driving route via Google Maps.")

    # details for public transport
    elif method_transport == 1:
        # showing connections that arrive approximately 30 minutes before the event starts
        event_dt = datetime.combine(start_date, start_time)
        query_dt = event_dt - timedelta(minutes=30)
        date_str = query_dt.strftime("%Y-%m-%d")
        time_str = query_dt.strftime("%H:%M")

        # getting three connections from the sbb open api
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

        # displaying the three options in a table
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

                    # formatting time
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

                    # getting platform details
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

                # dataframe with three columns to list the public transport connections
                df = pd.DataFrame(rows)[["Departure", "Arrival", "Train"]]

                # Index for the three connections
                df.index = [i + 1 for i in range(len(df))]
                df.index.name = "Connection"

                st.dataframe(df, width="stretched")
        
        # right column folium map
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
                "key": key, # using lokal key
            }

            g_resp = requests.get(g_url, params=g_params)
            g_data = g_resp.json()

            if g_data.get("status") == "OK":
                leg = g_data["routes"][0]["legs"][0]

                start_lat = leg["start_location"]["lat"]
                start_lng = leg["start_location"]["lng"]
                end_lat = leg["end_location"]["lat"]
                end_lng = leg["end_location"]["lng"]

                # placing map in the middle between origin and destination
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

                # polyline of the actual public transport route from google
                if "overview_polyline" in g_data["routes"][0]:
                    poly = g_data["routes"][0]["overview_polyline"]["points"]
                    coords = polyline.decode(poly)
                    folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)

                st_folium(m, height=210, width=500)
            else:
                st.warning("Could not retrieve transit route from Google Maps.")
    else:
        st.info("No transport method stored for this trip.")