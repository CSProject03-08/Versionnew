import streamlit as st

connections = results.get("connections", [])

for c in connections:
    dep = c["from"]["departure"]
    arr = c["to"]["arrival"]

    dep_time = dep["prognosis"]["departure"] or dep["scheduled"]
    arr_time = arr["prognosis"]["arrival"] or arr["scheduled"]

    travel_minutes = sbb.extract_travel_time(c)

    with st.expander(f"🚆 {dep_time} → {arr_time} ({travel_minutes} min)"):
        st.write(f"**Departure Platform:** {dep.get('platform', 'N/A')}")
        st.write(f"**Arrival Platform:** {arr.get('platform', 'N/A')}")
        st.write(f"**Transfers:** {len(c.get('sections', [])) - 1}")

        st.json(c)
