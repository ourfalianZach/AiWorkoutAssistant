import streamlit as st
from workoutPlanner import Exercise, WorkoutDay, WorkoutPlan
from appSetup import get_days_and_exercises


def edit_plan(conn, selected_plan_id, plans, selected_index):
    data = get_days_and_exercises(conn, selected_plan_id)

    workout_days = []
    current_day_id = None
    current_day = None
    exercises = []
    # each row is one exercise with its day info
    for row in data:
        day_id, day_name, focus, ex_name, sets, reps, rest_time, weight = row
        # is this a new day?
        if day_id != current_day_id:
            # if not first day, add the previous day to the workout days
            if current_day:
                current_day.exercises = exercises
                workout_days.append(current_day)

            # build new workout day
            current_day = WorkoutDay(day_name=day_name, focus=focus, exercises=[])
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
