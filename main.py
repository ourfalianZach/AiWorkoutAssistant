import openai
from dotenv import load_dotenv
import os
from workoutPlanner import (
    generate_workout_plan,
    what_to_do,
    parse_workout_plan,
    save_workout_plan,
)
from db import get_db_connection


load_dotenv()

conn = get_db_connection()

openai.api_key = os.getenv("OPENAI_API_KEY")

print("Welcome to the your AI workout assistant!")
query = input(
    "What do you need help with? (i.g. 'create a workout plan' or 'create a nutrition plan')\n"
)


response = what_to_do(query)

if response.assistant_type == "workout_planner":
    goal = input("What is your goal? (i.g. 'lose weight' or 'gain muscle')")
    time = int(input("How many minutes do you have to workout each day? "))
    days = int(input("How many days a week do you want to workout? "))

    response = generate_workout_plan(goal, time, days)
    workout_plan = parse_workout_plan(response)
    workout_plan.user_email = "user@example.com"
    print("\n Generated Workout Plan:")
    for day in workout_plan.workout_days:
        print(f"\n{day.day_name} - {day.focus}")
        for ex in day.exercises:
            print(f"  - {ex.name}: {ex.sets}x{ex.reps}, Rest: {ex.rest_time}s")
    workout_plan.user_email = "zach@example.com"
    save_workout_plan(workout_plan, conn)
    conn.close()
