import streamlit as st
import psycopg2
import psycopg2.extras
import bcrypt
from dotenv import load_dotenv
import os
import openai
from db import get_db_connection
from workoutPlanner import (
    generate_workout_plan,
    parse_workout_plan,
    save_workout_plan,
    Exercise,
    WorkoutDay,
    delete_workout_plan,
)


load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def register_user():
    st.sidebar.subheader("📝 Register")
    new_email = st.sidebar.text_input("Email", key="register_email")
    new_password = st.sidebar.text_input(
        "Password", type="password", key="register_password"
    )
    if st.sidebar.button("Register"):
        if not new_email or not new_password:
            st.error("Please fill in both fields.")
            return

        hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, password) VALUES (%s, %s)",
                    (new_email, hashed_pw),
                )
                conn.commit()
                st.success("✅ Registered! Please log in.")
        except psycopg2.errors.UniqueViolation:
            st.error("❌ Email already registered.")
        finally:
            conn.close()


def login_user():
    st.sidebar.subheader("🔐 Login")
    email = st.sidebar.text_input("Email", key="login_email")
    password = st.sidebar.text_input("Password", type="password", key="login_password")

    if st.sidebar.button("Log In"):
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
            st.session_state.user_email = user["email"]
            st.session_state.just_logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials.")


def logout_user():
    if st.sidebar.button("Log Out"):
        st.session_state.pop("user_email", None)
        st.session_state.pop("just_logged_in", None)
        st.rerun()


def get_all_plans(conn, user_email):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, goal, days_per_week, created_at
            FROM workout_plans
            WHERE user_email = %s
            ORDER BY created_at DESC
        """,
            (user_email,),
        )
        return cur.fetchall()


def get_days_and_exercises(conn, plan_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT wd.id, wd.day_name, wd.focus,
                   we.name, we.sets, we.reps, we.rest_time, we.weight
            FROM workout_days wd
            JOIN workout_exercises we ON wd.id = we.day_id
            WHERE wd.plan_id = %s
            ORDER BY wd.id, we.id
        """,
            (plan_id,),
        )
        return cur.fetchall()


# APP LOGIC STARTS HERE

st.set_page_config(page_title="🏋️ AI Workout Viewer")

if "user_email" not in st.session_state:
    st.sidebar.title("🔐 Account Access")
    register_user()
    login_user()
    st.stop()
else:
    st.sidebar.success(f"Logged in as: {st.session_state.user_email}")
    logout_user()

    if st.session_state.get("just_logged_in"):
        st.session_state.just_logged_in = False
        st.success(f"🎉 Welcome, {st.session_state.user_email}!")

if st.session_state.get("deleted_success"):
    st.success("✅ Plan deleted successfully!")
    del st.session_state["deleted_success"]


st.title("📋 Saved Workout Plan")

try:
    conn = get_db_connection()
    plans = get_all_plans(conn, st.session_state.user_email)

    if not plans:
        st.warning("No workout plans found for your account.")
        conn.close()
    else:
        # Render dropdown and plan viewer
        plan_labels = [
            f"Plan {i + 1}: {goal} ({days} days/week)"
            for i, (_, goal, days, _) in enumerate(plans)
        ]
        selected_label = st.selectbox("📅 Choose a plan to view:", plan_labels)
        selected_index = plan_labels.index(selected_label)
        selected_plan_id = plans[selected_index][0]

        st.subheader(plan_labels[selected_index])

        # ... (delete logic + display logic here)

        # Show plan summary
        st.caption(f"Created on {plans[selected_index][3]}")

        # --- Delete Option UI ---

        with st.expander("⚙️ Plan Actions"):
            if st.button("🗑️ Delete this plan"):
                st.session_state.show_confirm = True

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

        # ✅ Show success after rerun if needed
        if st.session_state.get("deleted_success"):
            st.success("✅ Plan deleted successfully!")
            del st.session_state["deleted_success"]

        # Display selected plan
        data = get_days_and_exercises(conn, selected_plan_id)
        current_day = None
        for row in data:
            day_id, day_name, focus, name, sets, reps, rest_time, weight = row
            if day_name != current_day:
                st.markdown(f"<h4>{day_name} – {focus}</h4>", unsafe_allow_html=True)
                current_day = day_name
            st.markdown(
                f"- **{name}**: {sets}x{reps}, Rest: {rest_time}s"
                + (f", Weight: {weight} lbs" if weight else "")
            )

        conn.close()

except Exception as e:
    st.error(f"❌ Database error: {e}")


st.title("🧠 Create a Workout Plan")
option = st.radio(
    "Choose how you'd like to create your plan:", ["Use GPT (AI)", "Input manually"]
)

if option == "Use GPT (AI)":
    if st.session_state.get("just_saved"):
        for field in ["goal", "time", "days"]:
            st.session_state.pop(field, None)
        st.session_state.pop("just_saved")

    goal = st.text_input("What is your goal?", key="goal")
    time = st.number_input(
        "How many minutes per day?", min_value=10, step=5, key="time"
    )
    days = st.slider("How many days per week?", 1, 7, key="days")

    if st.button("Generate with AI") and goal and time and days:
        with st.spinner("Generating plan..."):
            response = generate_workout_plan(goal, time, days)
            workout_plan = parse_workout_plan(response)
            workout_plan.user_email = st.session_state.user_email
            st.session_state.generated_plan = workout_plan
            st.success("✅ Plan generated!")

if st.session_state.get("generated_plan"):
    plan = st.session_state.generated_plan
    st.subheader("📝 Edit Your Plan Before Saving")

    updated_days = []
    for i, day in enumerate(plan.workout_days):
        st.markdown(f"### {day.day_name} – {day.focus}")
        updated_exercises = []
        ex_key = f"exercise_count_{i}"
        if ex_key not in st.session_state:
            st.session_state[ex_key] = len(day.exercises)

        for j in range(st.session_state[ex_key]):
            key_prefix = f"{i}_{j}"
            if j < len(day.exercises):
                ex = day.exercises[j]
            else:
                ex = Exercise(name="", sets=3, reps=10, rest_time=60, weight=None)

            col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
            with col1:
                name = st.text_input(
                    "Exercise", value=ex.name, key=f"ex_name_{key_prefix}"
                )
            with col2:
                sets = st.number_input(
                    "Sets", value=ex.sets, min_value=1, key=f"ex_sets_{key_prefix}"
                )
            with col3:
                try:
                    reps_val = int(ex.reps)
                except (ValueError, TypeError):
                    reps_val = 1

                reps = st.number_input(
                    "Reps", value=reps_val, min_value=1, key=f"ex_reps_{key_prefix}"
                )
            with col4:
                rest = st.number_input(
                    "Rest", value=ex.rest_time, min_value=0, key=f"ex_rest_{key_prefix}"
                )
            with col5:
                try:
                    weight_val = float(ex.weight)
                except (ValueError, TypeError):
                    weight_val = 0

                weight = st.number_input(
                    "Weight",
                    value=weight_val,
                    min_value=0,
                    key=f"ex_weight_{key_prefix}",
                )

            with col6:
                remove = st.checkbox("❌ Remove", key=f"ex_remove_{key_prefix}")

            if not remove:
                updated_exercises.append(
                    Exercise(
                        name=name,
                        sets=sets,
                        reps=reps,
                        rest_time=rest,
                        weight=weight if weight != 0 else None,
                    )
                )

        if st.button(f"➕ Add Exercise to {day.day_name}", key=f"add_exercise_btn_{i}"):
            st.session_state[ex_key] += 1

        updated_days.append(
            WorkoutDay(
                day_name=day.day_name, focus=day.focus, exercises=updated_exercises
            )
        )

    plan.workout_days = updated_days

    if st.button("💾 Save this plan"):
        conn = get_db_connection()
        save_workout_plan(plan, conn)
        conn.close()
        st.success("🎉 Plan saved to your account!")

        st.session_state["just_saved"] = True
        del st.session_state["generated_plan"]

        st.rerun()
