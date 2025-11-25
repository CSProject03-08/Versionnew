import sqlite3
import time
import streamlit as st
import pandas as pd
from api.api_city_lookup import get_city_coords
from ml.ml_model import retrain_model
from db.expenses_user import insert_expense_for_training
from datetime import date
from geopy.distance import geodesic
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "users.db")

### Connecting to the database trips.db ###
def connect():
    return sqlite3.connect(DB_PATH)

def employee_listview():
    """
    Returns all trips assigned to a given user (employee)
    using the user_trips mapping table and (for past trips)
    allows submitting an expense report via a wizard.
    """
    conn = connect()
    user_id = int(st.session_state["user_ID"])
    trip_df = pd.read_sql_query("""
        SELECT 
        t.trip_ID,
        t.origin,
        t.destination,
        t.start_date,
        t.end_date,
        t.start_time,
        t.end_time,
        t.occasion
        FROM trips t
        JOIN user_trips ut ON t.trip_ID = ut.trip_ID
        WHERE ut.user_ID = ?
        ORDER BY t.start_date ASC
        """, conn, params=(user_id,))
    conn.close()

    if trip_df.empty:
        st.info("No trips assigned yet.")
        return
    
    # ---- init expense wizard state once ----
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
    
    for _, row in trip_df.iterrows():
        start_date = pd.to_datetime(row.start_date).date()
        end_date = pd.to_datetime(row.end_date).date()

        trip_id = row.trip_ID
        is_active = wiz["active_trip_id"] == trip_id
        
        with st.expander(
            f"{row.trip_ID}: - {row.origin} → {row.destination} ({row.start_date} → {row.end_date})",
            expanded=is_active
        ):
            #list details
            st.write("**Occasion:**", row.occasion)
            st.write("**Start Date:**", row.start_date)
            st.write("**End Date:**", row.end_date)
            st.write("**Start Time:**", row.start_time)
            st.write("**End Time:**", row.end_time)

            #load participants into table
            conn = connect()
            participants = pd.read_sql_query("""
                SELECT u.username, u.email
                FROM users u
                JOIN user_trips ut ON ut.user_ID = u.user_ID
                WHERE ut.trip_ID = ?
                ORDER BY u.username
            """, conn, params=(row.trip_ID,))
            conn.close()

            st.markdown("**Participants:**")
            st.dataframe(participants, hide_index=True, use_container_width=True)
            
            # duration in days (for ML)
            duration_days = (end_date - start_date).days + 1

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
                # Wizard
                st.markdown("### Add business trip expense")
                cols_hdr = st.columns([1, 1])
                with cols_hdr[0]:
                    st.write(
                        "Please fill each category, upload receipts and "
                        "review everything before saving."
                    )
                    st.write(f"**Trip date:** {start_date} – {end_date}")
                    st.write(f"**Destination city:** {row.destination}")
                    st.write(f"**Duration (days):** {duration_days}")
                with cols_hdr[1]:
                    if st.button(
                        "✖ Close",
                        use_container_width=True,
                        key=f"close_{trip_id}",
                    ):
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
                    st.button(
                        "Next →",
                        type="primary",
                        on_click=_next,
                        key=f"next1_{trip_id}",
                    )
                    
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
                        st.button(
                            "← Back",
                            on_click=_back,
                            use_container_width=True,
                            key=f"back2_{trip_id}",
                        )
                    with c2:
                        st.button(
                            "Next →",
                            type="primary",
                            on_click=_next,
                            use_container_width=True,
                            key=f"next2_{trip_id}",
                        )

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
                        st.button(
                            "← Back",
                            on_click=_back,
                            use_container_width=True,
                            key=f"back3_{trip_id}",
                        )
                    with c2:
                        st.button(
                            "Next →",
                            type="primary",
                            on_click=_next,
                            use_container_width=True,
                            key=f"next3_{trip_id}",
                        )

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
                        st.button(
                            "← Back",
                            on_click=_back,
                            use_container_width=True,
                            key=f"back4_{trip_id}",
                        )
                    with c2:
                        st.button(
                            "Next →",
                            type="primary",
                            on_click=_next,
                            use_container_width=True,
                            key=f"next4_{trip_id}",
                        )

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
                        f"- **Hotel:** CHF {wiz['hotel_cost']:,.2f} "
                        f"({len(wiz['hotel_files'] or [])} file(s))\n"
                        f"- **Transportation:** CHF {wiz['transport_cost']:,.2f} "
                        f"({len(wiz['transport_files'] or [])} file(s))\n"
                        f"- **Meals:** CHF {wiz['meals_cost']:,.2f} "
                        f"({len(wiz['meals_files'] or [])} file(s))\n"
                        f"- **Other:** CHF {wiz['other_cost']:,.2f} "
                        f"({len(wiz['other_files'] or [])} file(s))\n"
                    )
                    st.markdown(
                        f"**Calculated total (CHF):** {total_cost:,.2f}"
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        st.button(
                            "← Back",
                            on_click=_back,
                            use_container_width=True,
                            key=f"back5_{trip_id}",
                        )
                    with c2:
                        if st.button(
                            "Save & Retrain",
                            type="primary",
                            use_container_width=True,
                            key=f"save_{trip_id}",
                        ):
                            # ---- 1. Compute distance between origin/destination for ML ----
                            origin_city = row.origin
                            dest_city = row.destination

                            origin_coords = get_city_coords(origin_city)
                            dest_coords = get_city_coords(dest_city)

                            if origin_coords and dest_coords:
                                from geopy.distance import geodesic

                                distance_km = geodesic(
                                    origin_coords, dest_coords
                                ).km
                            else:
                                distance_km = 0.0  # fallback

                            # ---- 2. Insert row into ML training DB ----
                            insert_expense_for_training(
                                dest_city=dest_city,
                                distance_km=distance_km,
                                duration_days=duration_days,
                                total_cost=total_cost,
                                user_id=user_id,
                            )

                            # ---- 3. Retrain ML model ----
                            mae = retrain_model()

                            st.success(
                                f"Expense saved and ML model retrained. MAE: {mae}"
                            )

                            # reset wizard
                            wiz.update(
                                active_trip_id=None,
                                step=1,
                                hotel_cost=0.0,
                                hotel_files=[],
                                transport_cost=0.0,
                                transport_files=[],
                                meals_cost=0.0,
                                meals_files=[],
                                other_cost=0.0,
                                other_files=[],
                            )
                            st.experimental_rerun()