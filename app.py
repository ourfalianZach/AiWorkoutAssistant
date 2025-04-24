import streamlit as st
import psycopg2
import psycopg2.extras
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()


# -----------------------------
# DB Connection
# -----------------------------
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
    )


# -----------------------------
# Registration
# -----------------------------
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
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, password) VALUES (%s, %s)",
                    (new_email, hashed_pw),
                )
                conn.commit()
                st.success("✅ Registered! Please log in.")
        except psycopg2.errors.UniqueViolation:
            st.error("🚫 Email already registered.")
        finally:
            conn.close()


# -----------------------------
# Login
# -----------------------------
def login_user():
    st.sidebar.subheader("🔐 Login")
    email = st.sidebar.text_input("Email", key="login_email")
    password = st.sidebar.text_input("Password", type="password", key="login_password")

    if st.sidebar.button("Log In"):
        conn = get_connection()
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


# -----------------------------
# Logout
# -----------------------------
def logout_user():
    if st.sidebar.button("Log Out"):
        st.session_state.pop("user_email", None)
        st.session_state.pop("just_logged_in", None)
        st.rerun()


# -----------------------------
# Get Latest Plan
# -----------------------------
def get_latest_plan(conn, user_email):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, goal, days_per_week, user_email, created_at
            FROM workout_plans
            WHERE user_email = %s
            ORDER BY id DESC
            LIMIT 1
        """,
            (user_email,),
        )
        return cur.fetchone()


# -----------------------------
# Get Plan Details
# -----------------------------
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


# -----------------------------
# Main App Logic
# -----------------------------
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

st.title("📋 Saved Workout Plan")

try:
    conn = get_connection()
    plan = get_latest_plan(conn, st.session_state.user_email)

    if plan:
        st.subheader(f"Goal: {plan[1]} ({plan[2]} days/week)")
        st.caption(f"Created by: {plan[3]} on {plan[4]}")

        data = get_days_and_exercises(conn, plan[0])
        current_day = None

        for row in data:
            day_id, day_name, focus, name, sets, reps, rest_time, weight = row
            if day_name != current_day:
                st.markdown(f"### {day_name} – {focus}")
                current_day = day_name
            st.markdown(
                f"- **{name}**: {sets}x{reps}, Rest: {rest_time}s"
                + (f", Weight: {weight} lbs" if weight else "")
            )
    else:
        st.warning("No workout plans found for your account.")
    conn.close()

except Exception as e:
    st.error(f"Database connection error: {e}")
