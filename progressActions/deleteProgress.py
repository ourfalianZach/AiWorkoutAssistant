import streamlit as st
from appSetup import get_db_connection


def deleteProgress(df, selected_row):
    if st.checkbox("Delete selected entry"):
        if st.button("🗑️ Confirm Delete"):
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM workout_progress WHERE user_email = %s AND completed_date = %s AND exercise_name = %s",
                    (
                        st.session_state.user_email,
                        df.at[selected_row, "Date"],
                        df.at[selected_row, "Exercise"],
                    ),
                )
                conn.commit()
            conn.close()
            st.success("✅ Progress entry deleted!")
            st.rerun()
