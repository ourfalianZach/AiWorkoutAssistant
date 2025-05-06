import streamlit as st
from appSetup import get_days_and_exercises, get_db_connection
from workoutPlanner import save_progress


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
        with st.expander(f"📈 Log Progress for {name}"):
            sets_done = st.number_input(
                "Sets done", min_value=0, key=f"sets_{day_id}_{name}"
            )
            reps_done = st.number_input(
                "Reps done", min_value=0, key=f"reps_{day_id}_{name}"
            )
            weight_used = st.number_input(
                "Weight used (lbs)", min_value=0, key=f"weight_{day_id}_{name}"
            )
            notes = st.text_area("Notes (optional)", key=f"notes_{day_id}_{name}")

            if st.button("Save Progress", key=f"save_progress_{day_id}_{name}"):
                conn = get_db_connection()
                save_progress(
                    conn,
                    st.session_state.user_email,
                    name,
                    day_name,
                    sets_done,
                    reps_done,
                    weight_used,
                    notes,
                )
                conn.close()
                st.success("✅ Progress saved!")
