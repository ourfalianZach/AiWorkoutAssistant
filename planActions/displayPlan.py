import streamlit as st
from appSetup import get_days_and_exercises


def display_plan(conn, selected_plan_id):
    data = get_days_and_exercises(conn, selected_plan_id)
    current_day = None
    for row in data:
        # instead of row[0], row[1] ... we use day_id, day_name ...
        day_id, day_name, focus, name, sets, reps, rest_time, weight = row

        if day_name != current_day:
            # using html to display day and focus
            st.markdown(f"<h4>{day_name} – {focus}</h4>", unsafe_allow_html=True)
            current_day = day_name

        # displays each exercise in a row
        st.markdown(
            f"- **{name}**: {sets}x{reps}, Rest: {rest_time}s"
            + (f", Weight: {weight} lbs" if weight else "")
        )
