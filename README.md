AiWorkoutAssistant is a full-featured AI-powered fitness app that lets users create, manage, and track personalized workout plans — all through a clean, interactive interface.
Users can generate workout plans in two ways:

AI-Generated Plans (GPT-4)
	•	Input fitness goal, available minutes per day, and days per week.
	•	The app uses OpenAI’s GPT API to generate a structured multi-day workout plan.
	•	The user can edit the plan before saving — including adding/removing exercises and modifying sets, reps, and weights.

Manual Plans
	•	Choose number of workout days per week.
	•	For each day, enter the focus area (e.g., “Chest and Triceps”) and add custom exercises with sets, reps, rest time, and weight.
	•	Dynamic UI lets users add more exercises per day as needed.

View Saved Workout Plans
	•	See all previously saved plans in a dropdown selector.
	•	Each plan includes its goal, structure, and exercises grouped by day.
	•	Cleanly formatted for easy viewing and reference.


Edit Existing Plans
	•	Re-open a saved plan and modify its structure:
	•	Add or remove exercises.
	•	Change any sets, reps, rest, or weights.
	•	Save your changes directly without creating a new plan.

Delete Workout Plans
	•	Remove any saved workout plan from your account with confirmation.
	•	Deleted plans are permanently removed from the database.

Track Workout Progress
	•	Log progress for specific exercises within any plan.
	•	For each entry, you can record:
	•	Day name
	•	Sets and reps completed
	•	Weight used
	•	Optional notes
	•	Date of completion
	•	Progress is tied to specific plans to match goals and training splits.

Visualize Your Progress
	•	Filter and view logged workouts by exercise name.
	•	View all past entries in a clean table format.
	•	See your weight progression over time in a line chart.

Modify or Delete Progress Entries
	•	Update any logged entry’s sets, reps, weight, notes, or date.
	•	Remove entries you no longer want with a single click.

•	Works with a PostgreSQL database.
•	Environment variables are managed with .env.
•	Built with Streamlit, Python, and OpenAI GPT API.


