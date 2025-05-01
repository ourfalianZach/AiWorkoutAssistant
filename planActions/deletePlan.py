import streamlit as st
from workoutPlanner import delete_workout_plan
from appSetup import get_db_connection


def delete_plan(conn, selected_plan_id):
    if st.session_state.get("show_confirm"):
        st.warning("⚠️ Are you sure you want to delete this plan?")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Yes, delete it"):
                conn = get_db_connection()
                delete_workout_plan(conn, selected_plan_id)
                conn.close()
                st.success("✅ Plan deleted successfully!")
                del st.session_state["show_confirm"]
                st.session_state["deleted_success"] = True
                st.rerun()

        with col2:
            if st.button("❌ No, cancel"):
                st.info("❌ Deletion cancelled.")
                del st.session_state["show_confirm"]
                st.rerun()

    # show success after rerun if needed
    if st.session_state.get("deleted_success"):
        st.success("✅ Plan deleted successfully!")
        del st.session_state["deleted_success"]
