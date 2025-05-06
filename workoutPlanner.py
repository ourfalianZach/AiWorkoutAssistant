import openai
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
import json
from dataclasses import dataclass


@dataclass
class Exercise:
    name: str
    sets: int
    reps: int
    rest_time: int
    weight: Optional[int] = None


@dataclass
class WorkoutDay:
    day_name: str
    focus: str
    exercises: List[Exercise] = None


@dataclass
class WorkoutPlan:
    goal: str = ""
    days_per_week: int = 0
    workout_days: List[WorkoutDay] = None
    user_email: Optional[str] = None


class AssistantType(BaseModel):
    assistant_type: Literal["workout_planner", "nutrition_planner"] = Field(
        description="The type of assistance being requested"
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    description: str = Field(
        description="A cleaned up description of the assistance being requested"
    )


def generate_workout_plan(goal: str, time: int, days: int):
    prompt = build_workout_prompt(goal, days, time)

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a fitness trainer looking to help your client achieve their goals.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content


def build_workout_prompt(goal: str, days: int, minutes: int):
    return f"""
    Act as a certified personal trainer. Create a structured weekly workout plan in JSON format only. 

    Details:
    - Goal: {goal}
    - Training Days: {days}
    - Session Length: {minutes} minutes
    - Assume the user is intermediate to advanced

    Use this exact JSON format:
    {{
        "goal": "{goal}",
        "days_per_week": {days},
        "workout_days": [
        {{
            "day_name": "Day 1",
            "focus": "Chest & Triceps",
            "exercises": [
            {{
                "name": "Bench Press",
                "sets": 3,
                 "reps": 10,
                "weight": null,
                "rest_time": 90
            }}, 
            ...
            ]   
        }},
        ...
        ]
    }}

    Respond ONLY with raw JSON.
    Do NOT say anything like "Here is your plan" or "Sure, here's your workout".
    Just return the JSON directly, and nothing else.
    Do not format it as a code block (no triple backticks).

    """


def parse_workout_plan(response: str) -> WorkoutPlan:
    data = json.loads(response)

    workout_days = []
    for day in data["workout_days"]:
        exercises = [
            Exercise(
                name=ex["name"],
                sets=ex["sets"],
                reps=ex["reps"],
                weight=ex.get("weight"),
                rest_time=ex.get("rest_time"),
            )
            for ex in day["exercises"]
        ]

        workout_day = WorkoutDay(
            day_name=day["day_name"], focus=day.get("focus"), exercises=exercises
        )
        workout_days.append(workout_day)

    return WorkoutPlan(
        goal=data["goal"],
        days_per_week=data["days_per_week"],
        workout_days=workout_days,
    )


def delete_workout_plan(conn, plan_id):
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM workout_plans WHERE id = %s", (plan_id,))
        conn.commit()
    except Exception:
        conn.rollback()


def clear_workout_plan_data(conn, plan_id):
    cursor = conn.cursor()

    # First delete exercises tied to the plan's days
    cursor.execute(
        """
        DELETE FROM workout_exercises
        WHERE day_id IN (
            SELECT id FROM workout_days WHERE plan_id = %s
        )
        """,
        (plan_id,),
    )

    # Then delete the days
    cursor.execute(
        """
        DELETE FROM workout_days
        WHERE plan_id = %s
        """,
        (plan_id,),
    )

    conn.commit()


def save_workout_plan(plan, conn, plan_id=None):
    cursor = conn.cursor()

    if plan_id:
        # Existing plan: update workout_plans basic info if needed (optional)
        cursor.execute(
            """
            UPDATE workout_plans
            SET goal = %s,
                days_per_week = %s
            WHERE id = %s
            """,
            (plan.goal, plan.days_per_week, plan_id),
        )
    else:
        # New plan: insert into workout_plans
        cursor.execute(
            """
            INSERT INTO workout_plans (user_email, goal, days_per_week)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (plan.user_email, plan.goal, plan.days_per_week),
        )
        plan_id = cursor.fetchone()[0]

    # Now insert workout_days and workout_exercises
    for day in plan.workout_days:
        cursor.execute(
            "INSERT INTO workout_days (plan_id, day_name, focus) VALUES (%s, %s, %s) RETURNING id",
            (plan_id, day.day_name, day.focus),
        )
        day_id = cursor.fetchone()[0]

        for ex in day.exercises:
            cursor.execute(
                """
                INSERT INTO workout_exercises (
                    day_id, name, sets, reps, rest_time, weight
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (day_id, ex.name, ex.sets, ex.reps, ex.rest_time, ex.weight),
            )

    conn.commit()


def save_progress(
    conn, user_email, exercise_name, day_name, sets_done, reps_done, weight_used, notes
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO workout_progress (
                user_email, exercise_name, day_name, sets_done, reps_done, weight_used, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
            (
                user_email,
                exercise_name,
                day_name,
                sets_done,
                reps_done,
                weight_used,
                notes,
            ),
        )
        conn.commit()
