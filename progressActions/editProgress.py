import streamlit as st
from appSetup import get_db_connection


def edit_progress(df, selected_row):
    if st.checkbox("Modify selected entry"):
        new_sets = st.number_input(
            "Sets", min_value=1, value=int(df.at[selected_row, "Sets"])
        )
        new_reps = st.number_input(
            "Reps", min_value=1, value=int(df.at[selected_row, "Reps"])
        )
        new_weight = st.number_input(
            "Weight", min_value=0, value=int(df.at[selected_row, "Weight"])
        )
        new_notes = st.text_area("Notes", value=df.at[selected_row, "Notes"] or "")

        if st.button("💾 Save Changes"):
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE workout_progress SET sets_done = %s, reps_done = %s, weight_used = %s, notes = %s WHERE user_email = %s AND completed_date = %s AND exercise_name = %s",
                    (
                        new_sets,
                        new_reps,
                        new_weight,
                        new_notes,
                        st.session_state.user_email,
                        df.at[selected_row, "Date"],
                        df.at[selected_row, "Exercise"],
                    ),
                )
                conn.commit()
            conn.close()
            st.success("✅ Progress entry updated!")
            st.rerun()
