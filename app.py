import streamlit as st
from dotenv import load_dotenv
import os
import openai
from workoutPlanner import (
    generate_workout_plan,
    parse_workout_plan,
    save_workout_plan,
    Exercise,
    WorkoutDay,
    delete_workout_plan,
    clear_workout_plan_data,
    WorkoutPlan,
)
from appSetup import (
    register_user,
    login_user,
    logout_user,
    get_all_plans,
    get_days_and_exercises,
    get_db_connection,
)

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


# APP LOGIC STARTS HERE

st.set_page_config(page_title="🏋️ AI Workout Viewer")


if "user_email" not in st.session_state:
    st.sidebar.title("🔐 Account Access")
    # App waits for user to log in or register
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

        # delete logic + display logic here

        # Show plan summary
        st.caption(f"Created on {plans[selected_index][3]}")

        # Delete Option UI

        with st.expander("⚙️ Plan Actions"):
            # EDIT PLAN LOGIC
            if st.button("✏️ Edit this plan"):
                data = get_days_and_exercises(conn, selected_plan_id)

                workout_days = []
                current_day_id = None
                current_day = None
                exercises = []
                # each row is one exercise with its day info
                for row in data:
                    day_id, day_name, focus, ex_name, sets, reps, rest_time, weight = (
                        row
                    )
                    # is this a new day?
                    if day_id != current_day_id:
                        # if not first day, add the previous day to the workout days
                        if current_day:
                            current_day.exercises = exercises
                            workout_days.append(current_day)

                        # build new workout day
                        current_day = WorkoutDay(
                            day_name=day_name, focus=focus, exercises=[]
                        )
                        # reset exercises list and update current day so we know what day we're in
                        exercises = []
                        current_day_id = day_id

                    # add exercise to the current day
                    exercises.append(
                        Exercise(
                            name=ex_name,
                            sets=sets,
                            reps=reps,
                            rest_time=rest_time,
                            weight=weight,
                        )
                    )

                # after loop add last day
                if current_day:
                    current_day.exercises = exercises
                    workout_days.append(current_day)

                # store the plan in the session state
                st.session_state.generated_plan = WorkoutPlan(
                    goal=plans[selected_index][1],
                    days_per_week=plans[selected_index][2],
                    workout_days=workout_days,
                    user_email=st.session_state.user_email,
                )

                # lets save button know it's editing a plan not creating a new one
                st.session_state.editing_plan_id = selected_plan_id

                # display message and reload app to see edits
                st.success("✏️ Plan loaded for editing!")
                st.rerun()
            # DELETE PLAN LOGIC
            # if you click on delete plan, it will show the confirm window
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

        conn.close()

except Exception as e:
    st.error(f"❌ Database error: {e}")


st.title("🧠 Create a Workout Plan")


option = st.radio(
    "Choose how you'd like to create your plan:",
    ["Use GPT (AI)", "Input manually"],
    key="option",
    index=None,
)


if option == "Use GPT (AI)":
    goal = st.text_input(
        "What is your goal?",
        # if goal is not in session state, it will be an empty string
        value=st.session_state.get("goal", ""),
        key="goal",
    )
    time = st.number_input(
        "How many minutes per day?",
        min_value=10,
        step=5,
        value=st.session_state.get("time", 60),
        key="time",
    )
    days = st.slider(
        "How many days per week?",
        1,
        7,
        value=st.session_state.get("days", 3),
        key="days",
    )
    # if all the fields are filled, the button will be enabled
    if st.button("Generate with AI") and goal and time and days:
        # creates a spinner to show that the plan is being generated
        with st.spinner("Generating plan..."):
            response = generate_workout_plan(goal, time, days)
            workout_plan = parse_workout_plan(response)
            workout_plan.user_email = st.session_state.user_email
            st.session_state.generated_plan = workout_plan
            st.success("✅ Plan generated!")
elif option == "Input manually":
    st.subheader("📝 Create Your Plan Manually")
    manual_goal = st.text_input("Goal:")
    num_days = st.number_input(
        "Days per week", min_value=1, step=1, key="num_manual_days"
    )

    manual_workout_days = []

    for i in range(int(num_days)):
        ex_key = f"manual_exercise_count_{i}"
        if ex_key not in st.session_state:
            st.session_state[ex_key] = 1  # default exercise is 1

        st.markdown(f"### Day {i + 1}")
        focus = st.text_input(f"Focus {i + 1}", key=f"focus_{i}")
        exercises = []

        for j in range(st.session_state[ex_key]):
            st.markdown(f"**Exercise {j + 1}**")
            name = st.text_input("Exercise Name", key=f"ex_name_{i}_{j}")
            sets = st.number_input("Sets", min_value=1, value=3, key=f"ex_sets_{i}_{j}")
            reps = st.number_input(
                "Reps", min_value=1, value=10, key=f"ex_reps_{i}_{j}"
            )
            rest = st.number_input(
                "Rest (seconds)",
                min_value=0,
                value=60,
                key=f"ex_rest_{i}_{j}",
            )
            weight = st.number_input(
                "Weight (lbs)", min_value=0, value=0, key=f"ex_weight_{i}_{j}"
            )
            exercises.append(
                Exercise(
                    name=name,
                    sets=sets,
                    reps=reps,
                    rest_time=rest,
                    weight=weight or None,
                )
            )
        manual_workout_days.append(
            WorkoutDay(day_name=f"Day {i + 1}", focus=focus, exercises=exercises)
        )
        if st.button(
            f" Add Exercise to Day {i + 1}", key=f"add_manual_exercise_btm_{i}"
        ):
            st.session_state[ex_key] += 1
    if st.button("💾 Save Manual Plan"):
        manual_plan = WorkoutPlan(
            goal=manual_goal,
            days_per_week=len(manual_workout_days),
            workout_days=manual_workout_days,
            user_email=st.session_state.user_email,
        )
        conn = get_db_connection()
        save_workout_plan(manual_plan, conn)
        conn.close()
        st.success("✅ Manual plan saved!")
        # Reset exercise count for each day to 1 after saving
        for i in range(len(manual_workout_days)):
            st.session_state[f"manual_exercise_count_{i}"] = 1
        # Clear manual input session state so form fields disappear
        del st.session_state["option"]
        st.session_state["option"] = None
        del st.session_state["num_manual_days"]
        for i in range(len(manual_workout_days)):
            del st.session_state[f"focus_{i}"]
            ex_key = f"manual_exercise_count_{i}"
            for j in range(st.session_state[ex_key]):
                for field in ["name", "sets", "reps", "rest", "weight"]:
                    key = f"ex_{field}_{i}_{j}"
                    if key in st.session_state:
                        del st.session_state[key]
            del st.session_state[ex_key]
        st.rerun()


# if the plan is generated, it will show the edit plan UI
if st.session_state.get("generated_plan"):
    plan = st.session_state.generated_plan
    st.subheader("📝 Edit Your Plan Before Saving")

    updated_days = []
    # for each day in the plan, it will show the day name and focus
    for i, day in enumerate(plan.workout_days):
        st.markdown(f"### {day.day_name} – {day.focus}")
        updated_exercises = []
        ex_key = f"exercise_count_{i}"
        # Has streamlit already created the exercise count for this day?
        if ex_key not in st.session_state:
            st.session_state[ex_key] = len(day.exercises)
        # if the exercise count is not in the session state, it will be created
        for j in range(st.session_state[ex_key]):  # for each exercise in the day
            key_prefix = f"{i}_{j}"
            if j < len(day.exercises):  # if 'j' is an original workout
                ex = day.exercises[j]
            else:  # if 'j' is a new workout added by user
                ex = Exercise(name="", sets=3, reps=10, rest_time=60, weight=None)

            # creates a column for each input field
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

            # if the remove checkbox is not checked, the exercise will be added to the updated exercises list
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
        # if the add exercise button is clicked, the exercise count will be incremented
        if st.button(f"➕ Add Exercise to {day.day_name}", key=f"add_exercise_btn_{i}"):
            st.session_state[ex_key] += 1

        # adds the updated exercises to the updated days list
        updated_days.append(
            WorkoutDay(
                day_name=day.day_name, focus=day.focus, exercises=updated_exercises
            )
        )  # end of for loop, it appends days whether updated or not to the updated days list

    # after all days are updated, the plan will be updated
    plan.workout_days = updated_days

    if st.button("💾 Save this plan"):
        conn = get_db_connection()

        if "editing_plan_id" in st.session_state:
            clear_workout_plan_data(conn, st.session_state.editing_plan_id)
            save_workout_plan(plan, conn, plan_id=st.session_state.editing_plan_id)
            del st.session_state["editing_plan_id"]
        else:
            save_workout_plan(plan, conn)

        conn.close()
        st.success("🎉 Plan saved to your account!")
        # deletes the fields from the session state so text fields are empty
        for field in ["goal", "time", "days"]:
            if field in st.session_state:
                del st.session_state[field]

        del st.session_state["generated_plan"]
        st.session_state["option"] = None
        st.rerun()
