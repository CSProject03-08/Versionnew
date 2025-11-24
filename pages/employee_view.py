import streamlit as st
from streamlit_option_menu import option_menu
import datetime
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from db.db_connection import Database
from db.db_class_events import Trips

st.set_page_config(page_title="Horizon Employee View", layout="wide")

# Initialize database connection
@st.cache_resource
def get_db_connection():
    db = Database()
    db.connect()
    return db

db = get_db_connection()
trips_manager = Trips(db)

# Navigation menu - horizontal at top
selected = option_menu(
    None,
    ["Dashboard", "Events", "Trips", "Tickets", "Profile"], 
    icons=['house', 'calendar', 'train', 'ticket', 'person'], 
    menu_icon="cast", 
    default_index=0,
    orientation="horizontal"
)

with st.sidebar:
    with st.popover("👤 Employee Login"):
        st.subheader("Select Your Account")
        selected_employee = st.selectbox(
            "Employee Name",
            ["John Smith", "Jane Doe", "Alice Johnson", "Bob Williams", "Emma Davis"],
            key="employee_selector"
        )
        if st.button("Login as Employee"):
            st.session_state['employee_name'] = selected_employee
            st.rerun()

st.title(f"Welcome, {st.session_state.get('employee_name', 'Employee')}!")

# Show content based on selected menu
if selected == "Dashboard":
    with st.container():
        
        # Get current employee name from session state (default for demo)
        current_employee = st.session_state.get('employee_name', 'John Smith')
        
        tab1, tab2, tab3 = st.tabs(["Next Trip", "Upcoming Trips", "Past Trips"])

    with tab1:
        st.header("Next Trip")
        next_trip = trips_manager.get_employee_next_trip(current_employee)
        
        if next_trip:
            trip = dict(next_trip)
            st.success("You have an upcoming trip!")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(f"✈️ {trip.get('destination', 'N/A')}")
                st.write(f"**From:** {trip.get('departure_location', 'N/A')}")
                st.write(f"**Departure:** {trip.get('departure_time', 'N/A')}")
                st.write(f"**Arrival:** {trip.get('arrival_time', 'N/A')}")
                st.write(f"**Status:** :green[{trip.get('status', 'pending').upper()}]")
            with col2:
                st.metric("Trip ID", trip.get('id'))
                if trip.get('event_id'):
                    st.metric("Event ID", trip.get('event_id'))
        else:
            st.info("No upcoming trips found.")
    
    with tab2:
        st.header("Upcoming Trips")
        upcoming_trips = trips_manager.get_employee_upcoming_trips(current_employee)
        
        if upcoming_trips:
            st.write(f"You have **{len(upcoming_trips)}** upcoming trip(s) after your next trip:")
            
            for trip in upcoming_trips:
                trip_dict = dict(trip)
                with st.expander(f"✈️ {trip_dict.get('destination', 'N/A')} - {trip_dict.get('departure_time', 'N/A')}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**From:** {trip_dict.get('departure_location', 'N/A')}")
                        st.write(f"**To:** {trip_dict.get('destination', 'N/A')}")
                        st.write(f"**Trip ID:** {trip_dict.get('id')}")
                    with col_b:
                        st.write(f"**Departure:** {trip_dict.get('departure_time', 'N/A')}")
                        st.write(f"**Arrival:** {trip_dict.get('arrival_time', 'N/A')}")
                        st.write(f"**Status:** {trip_dict.get('status', 'pending')}")
        else:
            st.info("No additional upcoming trips found.")  

    with tab3:
        st.header("Past Trips")
        past_trips = trips_manager.get_employee_past_trips(current_employee)

        # ---- initialise wizard state once ----
        if "expense_wizard" not in st.session_state:
            st.session_state.expense_wizard = {
                "active_trip_id": None,
                "step": 1,
                "hotel_cost": 0.0, "hotel_files": [],
                "transport_cost": 0.0, "transport_files": [],
                "meals_cost": 0.0, "meals_files": [],
                "other_cost": 0.0, "other_files": [],
            }
        wiz = st.session_state.expense_wizard

        # filter to trips truly in the past (arrival <= today)
        filtered_trips = []
        today = datetime.date.today()
        if past_trips:
            for trip in past_trips:
                arr = trip.get("arrival_time")
                try:
                    if isinstance(arr, datetime.datetime):
                        arr_date = arr.date()
                    elif isinstance(arr, dt.date):
                        arr_date = arr
                    else:
                        # if format is weird, just trust DB filtering
                        arr_date = today
                    if arr_date <= today:
                        filtered_trips.append(trip)
                except Exception:
                    filtered_trips.append(trip)

        if filtered_trips:
            st.write(f"You have completed **{len(filtered_trips)}** trip(s):")

            for trip in filtered_trips:
                trip_dict = dict(trip)
                trip_id = trip_dict.get("id")
                is_active = wiz["active_trip_id"] == trip_id

                # normalise dates for display + duration
                dep = trip_dict.get("departure_time")
                arr = trip_dict.get("arrival_time")
                if isinstance(dep, dt.datetime):
                    dep_date = dep.date()
                else:
                    dep_date = dep
                if isinstance(arr, dt.datetime):
                    arr_date = arr.date()
                else:
                    arr_date = arr
                try:
                    duration_days = (arr_date - dep_date).days + 1
                except Exception:
                    duration_days = 0

                label = f"✈️ {trip_dict.get('destination', 'N/A')} - {trip_dict.get('departure_time', 'N/A')}"
                with st.expander(label, expanded=is_active):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**From:** {trip_dict.get('departure_location', 'N/A')}")
                        st.write(f"**To:** {trip_dict.get('destination', 'N/A')}")
                        st.write(f"**Trip ID:** {trip_id}")
                    with col_b:
                        st.write(f"**Departure:** {trip_dict.get('departure_time', 'N/A')}")
                        st.write(f"**Arrival:** {trip_dict.get('arrival_time', 'N/A')}")
                        st.write(f"**Status:** {trip_dict.get('status', 'completed')}")

                    st.divider()

                    # ---- open wizard button (if not currently editing this trip) ----
                    if not is_active:
                        if st.button(
                            "➕ Submit expense report",
                            key=f"open_exp_{trip_id}",
                            type="primary",
                            use_container_width=True,
                        ):
                            wiz.update(
                                active_trip_id=trip_id,
                                step=1,
                                hotel_cost=0.0, hotel_files=[],
                                transport_cost=0.0, transport_files=[],
                                meals_cost=0.0, meals_files=[],
                                other_cost=0.0, other_files=[],
                            )
                            st.experimental_rerun()

                    else:
                        # ====== WIZARD (same structure as your old one, but trip data is pre-filled) ======
                        st.markdown("### Add business trip expense")
                        cols_hdr = st.columns([1, 1])
                        with cols_hdr[0]:
                            st.write("Please fill each category, upload receipts and review everything before saving.")
                            st.write(f"**Trip date:** {dep_date} – {arr_date}")
                            st.write(f"**Destination city:** {trip_dict.get('destination', 'N/A')}")
                            st.write(f"**Duration (days):** {duration_days}")
                        with cols_hdr[1]:
                            if st.button("✖ Close", use_container_width=True, key=f"close_{trip_id}"):
                                wiz["active_trip_id"] = None
                                wiz["step"] = 1
                                st.experimental_rerun()

                        step = wiz["step"]
                        st.markdown(f"#### Expense {step} of 5")

                        def _next():
                            wiz["step"] = min(5, wiz["step"] + 1)

                        def _back():
                            wiz["step"] = max(1, wiz["step"] - 1)

                        # ---------- Step 1: Hotel ----------
                        if step == 1:
                            wiz["hotel_cost"] = st.number_input(
                                "Total hotel cost (CHF)",
                                min_value=0.0,
                                step=10.0,
                                value=float(wiz["hotel_cost"]),
                                key=f"hotel_cost_{trip_id}",
                            )
                            wiz["hotel_files"] = st.file_uploader(
                                "📎 Upload hotel receipts (PDF or image)",
                                type=["pdf", "png", "jpg", "jpeg"],
                                accept_multiple_files=True,
                                key=f"hotel_files_upl_{trip_id}",
                            )
                            st.button("Next →", type="primary", on_click=_next, key=f"next1_{trip_id}")

                        # ---------- Step 2: Transportation ----------
                        elif step == 2:
                            wiz["transport_cost"] = st.number_input(
                                "Total transportation cost (CHF)",
                                min_value=0.0,
                                step=10.0,
                                value=float(wiz["transport_cost"]),
                                key=f"transport_cost_{trip_id}",
                            )
                            wiz["transport_files"] = st.file_uploader(
                                "📎 Upload transportation receipts (PDF or image)",
                                type=["pdf", "png", "jpg", "jpeg"],
                                accept_multiple_files=True,
                                key=f"transport_files_upl_{trip_id}",
                            )
                            c1, c2 = st.columns(2)
                            with c1:
                                st.button("← Back", on_click=_back, use_container_width=True, key=f"back2_{trip_id}")
                            with c2:
                                st.button("Next →", type="primary", on_click=_next, use_container_width=True, key=f"next2_{trip_id}")

                        # ---------- Step 3: Meals ----------
                        elif step == 3:
                            wiz["meals_cost"] = st.number_input(
                                "Total meals cost (CHF)",
                                min_value=0.0,
                                step=5.0,
                                value=float(wiz["meals_cost"]),
                                key=f"meals_cost_{trip_id}",
                            )
                            wiz["meals_files"] = st.file_uploader(
                                "📎 Upload meal receipts (PDF or image)",
                                type=["pdf", "png", "jpg", "jpeg"],
                                accept_multiple_files=True,
                                key=f"meals_files_upl_{trip_id}",
                            )
                            c1, c2 = st.columns(2)
                            with c1:
                                st.button("← Back", on_click=_back, use_container_width=True, key=f"back3_{trip_id}")
                            with c2:
                                st.button("Next →", type="primary", on_click=_next, use_container_width=True, key=f"next3_{trip_id}")

                        # ---------- Step 4: Other ----------
                        elif step == 4:
                            wiz["other_cost"] = st.number_input(
                                "Other costs (CHF)",
                                min_value=0.0,
                                step=5.0,
                                value=float(wiz["other_cost"]),
                                key=f"other_cost_{trip_id}",
                            )
                            wiz["other_files"] = st.file_uploader(
                                "📎 Upload other receipts (PDF or image)",
                                type=["pdf", "png", "jpg", "jpeg"],
                                accept_multiple_files=True,
                                key=f"other_files_upl_{trip_id}",
                            )
                            c1, c2 = st.columns(2)
                            with c1:
                                st.button("← Back", on_click=_back, use_container_width=True, key=f"back4_{trip_id}")
                            with c2:
                                st.button("Next →", type="primary", on_click=_next, use_container_width=True, key=f"next4_{trip_id}")

                        # ---------- Step 5: Review & Save ----------
                        elif step == 5:
                            total_cost = float(
                                wiz["hotel_cost"]
                                + wiz["transport_cost"]
                                + wiz["meals_cost"]
                                + wiz["other_cost"]
                            )
                            st.subheader("Review")
                            st.write(
                                f"- **Hotel:** CHF {wiz['hotel_cost']:,.2f} ({len(wiz['hotel_files'] or [])} file(s))\n"
                                f"- **Transportation:** CHF {wiz['transport_cost']:,.2f} ({len(wiz['transport_files'] or [])} file(s))\n"
                                f"- **Meals:** CHF {wiz['meals_cost']:,.2f} ({len(wiz['meals_files'] or [])} file(s))\n"
                                f"- **Other:** CHF {wiz['other_cost']:,.2f} ({len(wiz['other_files'] or [])} file(s))\n"
                            )
                            st.markdown(f"**Calculated total (CHF):** {total_cost:,.2f}")

                            c1, c2 = st.columns(2)
                            with c1:
                                st.button("← Back", on_click=_back, use_container_width=True, key=f"back5_{trip_id}")
                            with c2:
                                if st.button(
                                    "Save & Retrain",
                                    type="primary",
                                    use_container_width=True,
                                    key=f"save_{trip_id}",
                                ):
                                    # REMINDER: save expenses to your database (and save uploaded files somewhere)
                                    st.success("Expense saved and model retrained.")

                                    # reset wizard
                                    wiz.update(
                                        active_trip_id=None,
                                        step=1,
                                        hotel_cost=0.0, hotel_files=[],
                                        transport_cost=0.0, transport_files=[],
                                        meals_cost=0.0, meals_files=[],
                                        other_cost=0.0, other_files=[],
                                    )
                                    st.experimental_rerun()
        else:
            st.info("No past trips found.")

    with st.popover("Search Trips", use_container_width=True):

        st.write("🔍 Search Your Trips:")
        col1, col2 = st.columns(2)

        with col1:
            search_query = st.text_input("Enter destination or trip name", placeholder="e.g., Paris, New York")
        with col2:
            search_date = st.date_input("Enter Trip Date", value=None, help="Select a date to search for trips")

        # Search button
        if st.button("🔎 Search Trips", type="primary"):
            if search_query or search_date:
                with st.spinner("Searching for trips..."):
                    results = trips_manager.search_trips(
                        destination=search_query if search_query else None,
                        search_date=search_date if search_date else None
                )
            
            if results:
                st.success(f"Found {len(results)} trip(s)")
                
                # Display results in expandable cards
                for trip in results:
                    trip_dict = dict(trip)
                    with st.expander(f"✈️ {trip_dict.get('destination', 'N/A')} - {trip_dict.get('departure_time', 'N/A')}", expanded=True):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**Trip ID:** {trip_dict.get('id')}")
                            st.write(f"**Employee:** {trip_dict.get('employee_name', 'N/A')}")
                            st.write(f"**From:** {trip_dict.get('departure_location', 'N/A')}")
                            st.write(f"**To:** {trip_dict.get('destination', 'N/A')}")
                        with col_b:
                            st.write(f"**Departure:** {trip_dict.get('departure_time', 'N/A')}")
                            st.write(f"**Arrival:** {trip_dict.get('arrival_time', 'N/A')}")
                            st.write(f"**Status:** {trip_dict.get('status', 'pending')}")
                            if trip_dict.get('event_id'):
                                st.write(f"**Event ID:** {trip_dict.get('event_id')}")
            else:
                st.warning("No trips found matching your search criteria.")
        else:
            st.info("Please enter a destination or select a date to search.")

elif selected == "Events":
    # Import and display events page content
    from db.db_class_events import Events
    events_db = Events(db)
    
    st.title('Events')
    st.subheader('Upcoming events')
    
    # Display all events
    events_data = events_db.get_all_events()
    if events_data:
        events_list = [dict(event) for event in events_data]
        for event in events_list:
            with st.expander(f"📅 {event.get('name', 'N/A')} - {event.get('start_date', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Event Name:** {event.get('name', 'N/A')}")
                    st.write(f"**Location:** {event.get('location', 'N/A')}")
                with col2:
                    st.write(f"**Start Date:** {event.get('start_date', 'N/A')}")
                    st.write(f"**End Date:** {event.get('end_date', 'N/A')}")
    else:
        st.info("No events found. Create your first event below!")
    
    # Create new event form
    with st.form(key='create_event_form'):
        event_name = st.text_input("Event Name")    
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")
        location_name = st.text_input("Location")
        
        submitted = st.form_submit_button("Create Event")
        
        if submitted and event_name and location_name:
            events_db.create_event(event_name, start_date, end_date, location_name)
            st.success(f"Event '{event_name}' created successfully!")
            st.rerun()
        elif submitted:
            st.error("Please fill in Event Name and Location")

elif selected == "Trips":
    st.title('All Trips Overview')
    st.subheader('View all company trips')
    
    all_trips = trips_manager.get_all_trips()
    
    if all_trips:
        st.write(f"Total trips: **{len(all_trips)}**")
        
        for trip in all_trips:
            trip_dict = dict(trip)
            with st.expander(f"✈️ {trip_dict.get('destination', 'N/A')} - {trip_dict.get('employee_name', 'N/A')} - {trip_dict.get('departure_time', 'N/A')}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Trip ID:** {trip_dict.get('id')}")
                    st.write(f"**Employee:** {trip_dict.get('employee_name', 'N/A')}")
                    st.write(f"**From:** {trip_dict.get('departure_location', 'N/A')}")
                    st.write(f"**To:** {trip_dict.get('destination', 'N/A')}")
                with col_b:
                    st.write(f"**Departure:** {trip_dict.get('departure_time', 'N/A')}")
                    st.write(f"**Arrival:** {trip_dict.get('arrival_time', 'N/A')}")
                    st.write(f"**Status:** {trip_dict.get('status', 'pending')}")
                    if trip_dict.get('event_id'):
                        st.write(f"**Event ID:** {trip_dict.get('event_id')}")
    else:
        st.info("No trips found in the system.")

elif selected == "Profile":
    st.title('Employee Profile')
    st.subheader('Manage your profile information')
    
    current_employee = st.session_state.get('employee_name', 'Employee')
    
    st.write(f"**Name:** {current_employee}")
    st.write(f"**Department:** Travel & Operations")
    st.write(f"**Employee ID:** EMP-{hash(current_employee) % 10000:04d}")
    
    with st.form("profile_form"):
        st.subheader("Update Contact Information")
        email = st.text_input("Email", value=f"{current_employee.lower().replace(' ', '.')}@horizon.com")
        phone = st.text_input("Phone", value="+41 XX XXX XX XX")
        
        if st.form_submit_button("Update Profile"):
            st.success("Profile updated successfully!")

st.sidebar.markdown("© 2025 Horizon Inc.")