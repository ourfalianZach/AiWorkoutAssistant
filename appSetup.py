import streamlit as st
import psycopg2
import psycopg2.extras
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()


def register_user():
    st.sidebar.subheader("📝 Register")
    new_email = st.sidebar.text_input("Email", key="register_email")
    new_password = st.sidebar.text_input(
        "Password", type="password", key="register_password"
    )
    if st.sidebar.button("Register"):
        if not new_email or not new_password:
            st.error("Please fill both fields in.")
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
        # Use DictCursor to fetch user data as a dictionary
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        conn.close()

        # Check if user exists and password is correct
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


# one row per exercise
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


# connect to db
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
    )
