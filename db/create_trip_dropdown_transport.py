import streamlit as st
from api.api_transportation import transportation_managerview

def compare_transport_method(origin, destination):
    with st.form("transportcomparision"):
        st.markdown("---")
        st.subheader("Method of Transport")

        api_key = st.secrets["GOOGLE_API_KEY"]

        compare_clicked = st.form_submit_button("Do the comparison")

        if compare_clicked and origin and destination:
            st.session_state["transport_comparison_done"] = True
            transportation_managerview(origin, destination, api_key)
        else:
            if "transport_comparison_done" not in st.session_state:
                st.session_state["transport_comparison_done"] = False

        comparison_ready = st.session_state.get("transport_comparison_done", False)
        # 3) Auswahl der bevorzugten Transportmethode (zuerst ausgegraut)
        transport_method = st.selectbox(
            "Preferred transportation",
            ["Car", "Public transport"],
            disabled=not comparison_ready,
        )
        if not comparison_ready:
            st.caption(
                "Choose a transportation option after entering the API key and updating the comparison."
            )

        if comparison_ready:
            method_transport = 0 if transport_method == "Car" else 1
            return method_transport
