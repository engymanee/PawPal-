# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🛠️ Implementation Summary

The logic lives in `pawpal_system.py`:

- **Owner** has pets and the time they have available each day.
- **Pet** has care tasks (walks, feeding, meds, etc.).
- **Task** has a duration, priority, frequency, and an optional preferred time.
- **Scheduler** sorts the owner's tasks by priority, skips tasks that aren't due or don't fit, and places the rest in the owner's time windows.
- **DailyPlan** holds the result: scheduled tasks, skipped tasks, and a reason for each.

## 🖥️ Sample Output

========================================
Today's Schedule
========================================
Plan for Jordan on 2026-10-17
Scheduled:
  Buddy:
    07:30 - Morning walk (30 min) - High priority, scheduled at preferred time 07:30
    17:30 - Evening feeding (10 min) - Medium priority, scheduled at preferred time 17:30
  Whiskers:
    08:00 - Thyroid medication (5 min) - High priority, scheduled at preferred time 08:00
    18:00 - Laser pointer play (15 min) - Low priority, scheduled at preferred time 18:00
----------------------------------------
4 scheduled, 0 skipped, 60 of 120 minutes used
```

## 🧪 Testing PawPal+

The tests live in `tests/test_pawpal.py` and cover the logic in `pawpal_system.py`. The Streamlit UI is not tested automatically.

```bash
# Run the full test suite:
python -m pytest

# Verbose, one line per test:
python -m pytest -v

# Run a single test, or every test whose name matches a keyword:
python -m pytest tests/test_pawpal.py::test_find_conflicts_exact_same_time_and_no_conflicts
python -m pytest -k "conflict"
```

### What the tests verify

| Area                   | What is checked                                                                                                                                          |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Sorting correctness    | `sort_by_time()` returns tasks in chronological order across pets, puts tasks with no time last, keeps the original order for equal times, and handles empty input. `sort_tasks()` orders by priority, then time, then duration. |
| Recurrence logic       | Completing a daily task creates one new copy due tomorrow (weekly: in 7 days) on the same pet. The copy is skipped in today's plan and becomes due on its due date. Completing a task repeatedly never creates extra copies. |
| Conflict detection     | `find_conflicts()` flags tasks at the same time, for one pet or for different pets, and reports every pair when three or more collide. Back-to-back tasks and tasks without a time are not flagged. Warnings appear on the plan without stopping it from scheduling. |
| Plan generation        | Preferred times are used when free. Tasks are skipped, with a reason, when they are not due, when the owner is out of minutes, or when no time window has room. Scheduled tasks never overlap. |
| Models and filtering   | Pet/task and owner/pet links stay in sync, duplicates are ignored, errors are raised for tasks or pets that don't belong, and `filter_tasks()` filters by completion and pet name. |

A fuller list of planned cases and known gaps is in [TEST_PLAN.md](TEST_PLAN.md).

### Confidence level: ★★★★☆ (4 of 5)

All 43 tests pass, and they cover the behaviors that matter most: sorting, recurring tasks, conflict detection, and plan generation with skip reasons. I'm confident the core scheduling logic works as described.
It is not 5 stars because some edge cases are not tested yet

Sample test output:

```
============================= test session starts ==============================
collected 43 items

tests/test_pawpal.py ...........................................        [100%]

============================== 43 passed in 0.02s ==============================
```

## 📐 Smarter Scheduling

| Feature           | Method                       | What it does                                                                           |
|-------------------|------------------------------|----------------------------------------------------------------------------------------|
| Task sorting      | `Scheduler.sort_tasks()`     | Priority (high first), then preferred time, then shortest. Used by the scheduler.      |
| Task sorting      | `Scheduler.sort_by_time()`   | Preferred time only, earliest first. No-time tasks go last.                            |
| Filtering         | `Scheduler.filter_tasks()`   | By completion status and/or pet name (case-insensitive).                               |
| Filtering         | `Scheduler.generate_plan()`  | Skips tasks that are not due or don't fit, and records the reason.                     |
| Conflict handling | `Scheduler.find_conflicts()` | Returns a warning for each overlapping pair of preferred times. Never raises an error. |
| Recurring tasks   | `Task.mark_complete()`       | Creates the next copy: today + 1 day (daily) or + 7 days (weekly), using `timedelta`.  |
| Recurring tasks   | `Task.is_due_today()`        | Keeps the new copy unscheduled until its due date.                                     |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
