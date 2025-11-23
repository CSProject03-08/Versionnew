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
        
        if past_trips:
            st.write(f"You have completed **{len(past_trips)}** trip(s):")
            
            for trip in past_trips:
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
                        st.write(f"**Status:** {trip_dict.get('status', 'completed')}")
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