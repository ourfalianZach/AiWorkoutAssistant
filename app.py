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
    clear_workout_plan_data,
    WorkoutPlan,
)
from appSetup import (
    register_user,
    login_user,
    logout_user,
    get_all_plans,
    get_db_connection,
)
from planActions.editPlan import edit_plan
from planActions.deletePlan import delete_plan
from planActions.displayPlan import display_plan
from progressActions.editProgress import edit_progress
from progressActions.deleteProgress import deleteProgress

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

tabs = st.tabs(["Workout Plan", "Progress Tracker"])
with tabs[0]:
    if st.session_state.get("deleted_success"):
        st.success("✅ Plan deleted successfully!")
        del st.session_state["deleted_success"]

    st.title("📋 Saved Workout Plan")

    try:
        conn = get_db_connection()
        plans = get_all_plans(conn, st.session_state.user_email)

        if not plans:
            st.warning(
                "No workout plans found for your account! Please create a new plan."
            )
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

            # Show plan summary
            st.caption(f"Created on {plans[selected_index][3]}")

            # plan action UI

            with st.expander("⚙️ Plan Actions"):
                # EDIT PLAN LOGIC
                if st.button("✏️ Edit this plan"):
                    edit_plan(conn, selected_plan_id, plans, selected_index)

                # DELETE PLAN LOGIC
                # if you click on delete plan, it will show the confirm window
                if st.button("🗑️ Delete this plan"):
                    st.session_state.show_confirm = True

            # will only run if the confirm window is clicked
            delete_plan(conn, selected_plan_id)

            # Display selected plan
            display_plan(conn, selected_plan_id=selected_plan_id)

            conn.close()

    except Exception as e:
        st.error(f"❌ Database error: {e}")

    st.title("🧠 Create a Workout Plan")
    if st.session_state.get("reset_option"):
        st.session_state["option"] = None
        del st.session_state["reset_option"]
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
        # iterates over each workout day
        for i in range(int(num_days)):
            # ex_key is the exercise count for the day
            ex_key = f"manual_exercise_count_{i}"
            if ex_key not in st.session_state:
                st.session_state[ex_key] = 1  # default exercise is 1

            st.markdown(f"### Day {i + 1}")
            focus = st.text_input(f"Focus {i + 1}", key=f"focus_{i}")
            exercises = []

            # iterates over each exercise added so far in the day
            for j in range(st.session_state[ex_key]):
                st.markdown(f"**Exercise {j + 1}**")
                name = st.text_input("Exercise Name", key=f"ex_name_{i}_{j}")
                sets = st.number_input(
                    "Sets", min_value=1, value=3, key=f"ex_sets_{i}_{j}"
                )
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
                # adds the exercise to the exercises list
                exercises.append(
                    Exercise(
                        name=name,
                        sets=sets,
                        reps=reps,
                        rest_time=rest,
                        weight=weight or None,
                    )
                )
            # creates a workout day with the exercises and adds it to the manual workout days list
            manual_workout_days.append(
                WorkoutDay(day_name=f"Day {i + 1}", focus=focus, exercises=exercises)
            )
            # if button is clicked, the exercise count will be incremented so another input set is shown
            if st.button(
                f" Add Exercise to Day {i + 1}", key=f"add_manual_exercise_btm_{i}"
            ):
                st.session_state[ex_key] += 1

        if st.button("💾 Save Manual Plan"):
            # creates full workout plan object with user entered info
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
            # reset exercise count for each day to 1 after saving
            for i in range(len(manual_workout_days)):
                st.session_state[f"manual_exercise_count_{i}"] = 1
            # reset radio
            st.session_state["reset_option"] = True
            st.session_state["manual_plan_saved"] = True
            # reset number of days
            del st.session_state["num_manual_days"]
            # clear user input fields
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

    if st.session_state.get("manual_plan_saved"):
        del st.session_state["manual_plan_saved"]
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
                        "Rest",
                        value=ex.rest_time,
                        min_value=0,
                        key=f"ex_rest_{key_prefix}",
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
            if st.button(
                f"➕ Add Exercise to {day.day_name}", key=f"add_exercise_btn_{i}"
            ):
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
            st.rerun()
with tabs[1]:
    st.title("📈 View Workout Progress")

    conn = get_db_connection()
    plans = get_all_plans(conn, st.session_state.user_email)

    if not plans:
        st.warning("No workout plans found.")
        conn.close()
    else:
        plan_labels = [
            f"Plan {i + 1}: {goal} ({days} days/week)"
            for i, (_, goal, days, _) in enumerate(plans)
        ]
        selected_label = st.selectbox(
            "📈 Select a plan to view progress:",
            plan_labels,
            key="progress_plan_select",
        )
        selected_index = plan_labels.index(selected_label)
        selected_plan_id = plans[selected_index][0]

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT exercise_name, day_name, sets_done, reps_done, weight_used, notes, completed_date
                FROM workout_progress
                WHERE user_email = %s AND plan_id = %s
                ORDER BY completed_date DESC
                """,
                (st.session_state.user_email, selected_plan_id),
            )
            progress = cur.fetchall()
        conn.close()

        if not progress:
            st.info("No progress data yet. Log some workouts!")
        else:
            import pandas as pd

            df = pd.DataFrame(
                progress,
                columns=["Exercise", "Day", "Sets", "Reps", "Weight", "Notes", "Date"],
            )
            st.table(df.reset_index(drop=True).style.hide(axis="index"))
            # --- Edit/Delete Section ---
            st.markdown("### ✏️ Edit or Delete Progress Entry")

            # Use DataFrame's index for selection
            selected_row = st.selectbox(
                "Select a progress entry to modify:",
                df.index,
                format_func=lambda i: f"{df.at[i, 'Exercise']} on {df.at[i, 'Date']}",
            )
            edit_progress(df, selected_row)
            # if st.checkbox("Edit selected entry"):
            #     new_sets = st.number_input(
            #         "Sets", min_value=1, value=int(df.at[selected_row, "Sets"])
            #     )
            #     new_reps = st.number_input(
            #         "Reps", min_value=1, value=int(df.at[selected_row, "Reps"])
            #     )
            #     new_weight = st.number_input(
            #         "Weight", min_value=0, value=int(df.at[selected_row, "Weight"])
            #     )
            #     new_notes = st.text_area(
            #         "Notes", value=df.at[selected_row, "Notes"] or ""
            #     )

            #     if st.button("💾 Save Changes"):
            #         conn = get_db_connection()
            #         with conn.cursor() as cur:
            #             cur.execute(
            #                 "UPDATE workout_progress SET sets_done = %s, reps_done = %s, weight_used = %s, notes = %s WHERE user_email = %s AND completed_date = %s AND exercise_name = %s",
            #                 (
            #                     new_sets,
            #                     new_reps,
            #                     new_weight,
            #                     new_notes,
            #                     st.session_state.user_email,
            #                     df.at[selected_row, "Date"],
            #                     df.at[selected_row, "Exercise"],
            #                 ),
            #             )
            #             conn.commit()
            #         conn.close()
            #         st.success("✅ Progress entry updated!")
            #         st.rerun()
            deleteProgress(df, selected_row)
            # if st.checkbox("Delete selected entry"):
            #     if st.button("🗑️ Confirm Delete"):
            #         conn = get_db_connection()
            #         with conn.cursor() as cur:
            #             cur.execute(
            #                 "DELETE FROM workout_progress WHERE user_email = %s AND completed_date = %s AND exercise_name = %s",
            #                 (
            #                     st.session_state.user_email,
            #                     df.at[selected_row, "Date"],
            #                     df.at[selected_row, "Exercise"],
            #                 ),
            #             )
            #             conn.commit()
            #         conn.close()
            #         st.success("✅ Progress entry deleted!")
            #         st.rerun()

            # --- End Edit/Delete Section ---

            if st.checkbox("📊 Show chart by exercise"):
                exercise_options = df["Exercise"].unique()
                selected_ex = st.selectbox("Select an exercise", exercise_options)
                ex_data = df[df["Exercise"] == selected_ex]
                st.line_chart(ex_data[["Date", "Weight"]].set_index("Date"))
