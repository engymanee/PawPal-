# 🐾 PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

**Contents:** [Scenario](#scenario) · [Getting started](#getting-started) · [Features](#-features) · [Quick start](#-quick-start) · [How it works](#-how-it-works) · [Demo](#-demo-walkthrough) · [Testing](#-testing) · [Project files](#-project-files)

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

## ✨ Features

| Feature | What it does |
|---|---|
| **Priority ordering** | `sort_by_priority()` (and `sort_tasks()`, which uses it) orders tasks high, medium, low. Ties go to the earlier preferred time (tasks with no time come after), then the shorter task. The app's "Sort by" box offers it. |
| **Sorting by time** | `sort_by_time()` orders tasks by preferred time, earliest first, no-time tasks last. The sort is stable and never changes the input list. |
| **Filtering** | `filter_tasks()` filters by completion status, by pet name (case-insensitive), or both. A task counts as completed once it is done and not due again yet. |
| **Greedy daily planning** | `generate_plan()` walks the tasks in priority order and places each one if it is due and fits. When time runs short, the lowest-priority tasks are left out. |
| **Optimal planning** | `optimal_plan()` searches for the highest-scoring plan instead of placing tasks greedily. Each task is skipped or placed at a start time in a window. It scores 10 / 5 / 2 points by priority (high / medium / low), minus 1 point for every 15 minutes it is moved from its preferred time. The plan must fit the available minutes, never overlap, respect dependencies and minimum gaps, and keep every must-do task. See [Optimal planner](#optimal-planner). |
| **Dependencies** | `Task.depends_on` lists titles of the same pet's tasks that must come first. `order_by_dependencies()` sorts with Kahn's algorithm and raises `DependencyCycleError` with the loop (for example `A -> B -> A`). |
| **Next free slot** | `find_next_available_slot()` returns the first gap in today's plan that fits a task of a given length, not before a given time. It returns `None` when nothing fits or too few minutes are left. |
| **Time budget check** | Each task is checked against the owner's remaining minutes. A task that does not fit is skipped, and the reason gives the minutes needed and left. |
| **Time-window placement** | Each time window keeps a cursor at its next free minute. A task goes at its preferred time when that falls inside a window with room, otherwise in the earliest window with space. The cursor only moves forward, so scheduled tasks never overlap. With no windows set, 08:00-20:00 is used. |
| **Conflict warnings** | `find_conflicts()` treats each due task with a preferred time as a range (start to start + duration), sorts the ranges by start, and compares each only with those that start before it ends. Back-to-back tasks are not flagged. Same-pet and different-pet overlaps get different messages. Warnings never stop the plan. |
| **Recurring tasks** | `mark_complete()` records today's date and creates one copy due in 1 day (daily) or 7 days (weekly) with `timedelta`, on the same pet. Completing a task again returns the existing copy. |
| **Due-date logic** | `is_due_today()` is false for a task that already has a next copy and for a copy due in the future. Otherwise a task is due if never completed, or if enough days have passed (1 daily, 7 weekly). |
| **Readable CLI output** | The demo in `main.py` prints tabulate tables with category emojis, priority colors and a time-budget bar. See [CLI formatting](#cli-formatting). |
| **Explained results** | Every scheduled or skipped task carries a reason. `explain_choice()` looks it up for any task. |
| **Input checks (UI)** | Blank or duplicate pet names and duplicate task titles per pet are rejected. A warning appears when tasks due today exceed the owner's available minutes. |

## 🚀 Quick start

After the [setup](#setup) above:

```bash
streamlit run app.py   # launch the app
python main.py         # or run the scripted CLI demo
python -m pytest       # run the tests
```

## 🧩 How it works

The logic lives in [pawpal_system.py](pawpal_system.py). The Streamlit UI in [app.py](app.py) only displays it.

| Class | Role |
|---|---|
| `Owner` | Has pets, the minutes available each day, and optional time windows. |
| `Pet` | Has care tasks (walks, feeding, meds, enrichment, grooming). |
| `Task` | Has a duration, priority, frequency, optional preferred time, recurrence state, and optional dependencies and minimum gap. |
| `Scheduler` | Sorts, filters, checks conflicts, finds free slots, and builds the plan (greedy `generate_plan()` or `optimal_plan()`). |
| `DailyPlan` | The result: scheduled tasks, skipped tasks, warnings, and a reason for each. |

Class diagrams: [diagrams/uml_final.mmd](diagrams/uml_final.mmd) is exactly what was built, and [diagrams/uml.mmd](diagrams/uml.mmd) is the design diagram. GitHub renders `.mmd` files only inside Markdown, so paste one into a `mermaid` code block or the [Mermaid Live Editor](https://mermaid.live) to view it.

## 🎬 Demo walkthrough

### What you can do in the app

| Section | Actions |
|---|---|
| **Owner** | Set your name and the minutes you have available today. |
| **Add a Pet** | Enter name, species, breed, age and special needs. Remove a pet (and its tasks). |
| **Add a Task** | Pick a pet, then set title, category, duration, priority, frequency and an optional preferred time. |
| **Current tasks** | Filter by pet and status (Pending, Completed, All). The table is sorted by preferred time. Mark a task complete or remove it. |
| **Build Schedule** | See metrics (scheduled, skipped, minutes used), the schedule with a reason per task, and any warnings. |

### Example workflow

1. Set the owner to "Jordan" with 120 minutes available.
2. Add a pet: "Buddy", a dog.
3. Add a task for Buddy: "Morning walk", walk, 30 minutes, high priority, daily, preferred time 07:30.
4. Add a second pet, "Whiskers", and a task: "Thyroid medication", 5 minutes, high priority, also at 07:30.
5. Scroll to **Build Schedule**. A conflict warning appears because both tasks want 07:30. Both are still scheduled: the walk at 07:30 and the medication right after it, each with a reason.
6. Click **Mark complete** on "Morning walk". It leaves the Pending list, a copy due tomorrow is created, and today's plan no longer includes it.

### Scheduler behaviors you can see

- **Sorting:** the task list is ordered by preferred time. The planner itself works by priority, then time, then duration.
- **Filtering:** the pet and status dropdowns use `filter_tasks()`.
- **Conflict warnings:** overlapping preferred times are flagged, for the same pet or different pets. Back-to-back tasks are not.
- **Time budget:** a warning appears when tasks due today exceed your available minutes. The lowest-priority tasks are skipped, with the reason shown.
- **Recurring tasks:** completing a daily or weekly task creates the next copy, which stays out of today's plan until it is due.

### Optimal planner

`generate_plan()` is greedy: it takes tasks in priority order and keeps each one that fits. That can miss a better plan, for example a 60-minute high-priority grooming that leaves no room for three 20-minute walks that together score more. `optimal_plan()` fixes this by searching.

- **Search:** a depth-first search over the due tasks, in dependency order (Kahn's algorithm). Each task is skipped, or placed at a start time inside a time window (every 15 minutes, its preferred time, and right after tasks already placed). A branch is dropped once its score plus the value of every task still undecided cannot beat the best plan found (branch and bound).
- **Constraints:** time windows, the owner's available minutes, no overlaps, dependencies (a task starts after the tasks it depends on end), and minimum gaps (`min_gap_minutes` between two tasks of the same pet and category, measured from one task's end to the next one's start).
- **Must-do tasks:** high-priority meds are never skipped. If they cannot fit, `MustDoError` explains why, for example "Insulin needs 90 min but only 60 are available".
- **Explanations:** a placed task shows its points and any move ("moved to 07:15 from 07:00 (-1 pts) because it must come after 'Breakfast'"). A skipped task shows the score of the best plan that includes it against the chosen plan.
- **Limits:** the search stops after 50,000 steps and adds a warning that the plan may not be optimal. The "why skipped" checks stop after 5,000 steps. A skipped task whose dependency is skipped is skipped too, and a dependency that is not due today counts as met.
- **In the app:** the Build Schedule section has a "Planner" switch between Greedy and Optimal. The Add Task form has "Must come after" and "Minimum gap" fields. In the CLI, the demo ends with a section comparing the two planners.

### CLI formatting

The formatting lives in [main.py](main.py) only. `pawpal_system.py` still returns plain data, and `DailyPlan.display()` keeps its plain-text output, so the tests and the Streamlit UI are unaffected.

**Libraries**

| Library | Used for |
|---|---|
| [tabulate](https://pypi.org/project/tabulate/) | Draws every list as a `rounded_outline` table (`tabulate(rows, headers=..., tablefmt="rounded_outline")`). It aligns columns and numbers and ignores the color codes when measuring width. |
| [wcwidth](https://pypi.org/project/wcwidth/) | Used by tabulate, when installed, to measure emoji as two columns wide so the table borders stay aligned. |
| `os` and `sys` (standard library) | `sys.stdout.isatty()` and `os.environ` decide whether to print colors. |

Both libraries are listed in [requirements.txt](requirements.txt), so `pip install -r requirements.txt` installs them.

**Features**

| Feature | How it works |
|---|---|
| **Structured tables** | Tasks, the day's schedule, skipped tasks, recurring tasks and free-slot results each print as a table with a header row. |
| **Emoji per task category** | `CATEGORY_ICONS` maps 🦮 walk, 🍖 feeding, 💊 meds, 🎾 enrichment and 🧼 grooming. `task_label()` puts the icon before the title. |
| **Priority indicators** | `PRIORITY_STYLE` maps high, medium and low to 🔴, 🟡 and 🟢 plus a color. `priority_label()` builds labels such as "🔴 High". |
| **Color-coded output** | `paint(text, style)` wraps text in an ANSI escape code (red, yellow, green, cyan, bold or dim). It colors priority names, the ✅ PASS / ❌ FAIL and slot results, and section banners. |
| **Colors that switch off** | `USE_COLOR` is false when output is piped or redirected, or when the `NO_COLOR` environment variable is set. Emojis and tables still print. The sample below was captured this way. |
| **Time-budget bar** | A 20-character `█░` bar for minutes used out of minutes available. It is green below 80%, yellow from 80%, and red when the budget is full. |
| **Status markers** | ⚠ for each conflict warning, 💤 for the skipped-tasks table, ✅ and ❌ for pass/fail and slot results. |
| **Section banners** | `banner(title)` prints a cyan ruled heading for each part of the demo. |

**Helper functions in `main.py`**

| Function | Purpose |
|---|---|
| `paint(text, style)` | Add an ANSI color or style when color is enabled. |
| `priority_label(task)` | Priority dot and colored priority name. |
| `task_label(task)` | Category emoji and task title. |
| `table(rows, headers)` | Print rows with tabulate, indented two spaces. |
| `banner(title)` | Print a section heading. |

### Sample CLI output

`python main.py` runs a scripted demo of the same logic without the UI. It prints [tabulate](https://pypi.org/project/tabulate/) tables with an emoji per task category (🦮 walk, 🍖 feeding, 💊 meds, 🎾 enrichment, 🧼 grooming) and a priority dot (🔴 high, 🟡 medium, 🟢 low). In a terminal the priority names, ✅/❌ results and the time-budget bar are also colored (green, yellow or red); colors turn off when output is piped or `NO_COLOR` is set, as in the capture below. The output is real and shows each scheduling feature in turn:

- `sort_by_time()` vs `sort_by_priority()`: the first orders by clock time only, so the low-priority Early snack (06:30) comes first. The second puts high-priority tasks first, then medium, then low, using time to break ties, so Early snack drops below Evening feeding.
- `find_conflicts()` for same-pet, different-pet and identical-time overlaps.
- `generate_plan()` with a reason for every scheduled or skipped task.
- `optimal_plan()` against `generate_plan()` on a case where greedy loses, with dependency, spacing, cycle and must-do examples at the end.
- `find_next_available_slot()`, which finds the first gap in today's plan that fits a new task. A 15-minute task fits at 07:00. The 20- and 30-minute requests return no slot because only 15 of the owner's 120 minutes are left, even though the 17:00-20:00 window still has gaps.

<details>
<summary>Show output</summary>

```
🔁 Recurring tasks created:
  ╭──────────┬───────────────────────┬─────────────┬────────────╮
  │ Pet      │ Task                  │ Frequency   │ Next due   │
  ├──────────┼───────────────────────┼─────────────┼────────────┤
  │ Whiskers │ 💊 Thyroid medication │ daily       │ 2026-10-18 │
  │ Buddy    │ 🦮 Morning walk       │ daily       │ 2026-10-18 │
  ╰──────────┴───────────────────────┴─────────────┴────────────╯

========================================================
 🔎 Sorting and filtering checks
========================================================

As added (out of order):
  ╭────────┬──────────┬───────────────────────┬───────┬────────────╮
  │ Time   │ Pet      │ Task                  │   Min │ Priority   │
  ├────────┼──────────┼───────────────────────┼───────┼────────────┤
  │ 17:30  │ Buddy    │ 🍖 Evening feeding    │    10 │ 🟡 Medium  │
  │ --:--  │ Buddy    │ 🧼 Brush coat         │    10 │ 🟢 Low     │
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 06:30  │ Buddy    │ 🍖 Early snack        │     5 │ 🟢 Low     │
  │ 18:00  │ Whiskers │ 🎾 Laser pointer play │    15 │ 🟢 Low     │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  ╰────────┴──────────┴───────────────────────┴───────┴────────────╯

sort_by_time():
  ╭────────┬──────────┬───────────────────────┬───────┬────────────╮
  │ Time   │ Pet      │ Task                  │   Min │ Priority   │
  ├────────┼──────────┼───────────────────────┼───────┼────────────┤
  │ 06:30  │ Buddy    │ 🍖 Early snack        │     5 │ 🟢 Low     │
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  │ 17:30  │ Buddy    │ 🍖 Evening feeding    │    10 │ 🟡 Medium  │
  │ 18:00  │ Whiskers │ 🎾 Laser pointer play │    15 │ 🟢 Low     │
  │ --:--  │ Buddy    │ 🧼 Brush coat         │    10 │ 🟢 Low     │
  ╰────────┴──────────┴───────────────────────┴───────┴────────────╯

sort_by_priority() [priority first, then time]:
  ╭────────┬──────────┬───────────────────────┬───────┬────────────╮
  │ Time   │ Pet      │ Task                  │   Min │ Priority   │
  ├────────┼──────────┼───────────────────────┼───────┼────────────┤
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  │ 17:30  │ Buddy    │ 🍖 Evening feeding    │    10 │ 🟡 Medium  │
  │ 06:30  │ Buddy    │ 🍖 Early snack        │     5 │ 🟢 Low     │
  │ 18:00  │ Whiskers │ 🎾 Laser pointer play │    15 │ 🟢 Low     │
  │ --:--  │ Buddy    │ 🧼 Brush coat         │    10 │ 🟢 Low     │
  ╰────────┴──────────┴───────────────────────┴───────┴────────────╯

filter_tasks(pet_name='Buddy'):
  ╭────────┬───────┬────────────────────┬───────┬────────────╮
  │ Time   │ Pet   │ Task               │   Min │ Priority   │
  ├────────┼───────┼────────────────────┼───────┼────────────┤
  │ 17:30  │ Buddy │ 🍖 Evening feeding │    10 │ 🟡 Medium  │
  │ --:--  │ Buddy │ 🧼 Brush coat      │    10 │ 🟢 Low     │
  │ 07:30  │ Buddy │ 🦮 Morning walk    │    30 │ 🔴 High    │
  │ 07:30  │ Buddy │ 🦮 Morning walk    │    30 │ 🔴 High    │
  │ 06:30  │ Buddy │ 🍖 Early snack     │     5 │ 🟢 Low     │
  ╰────────┴───────┴────────────────────┴───────┴────────────╯

filter_tasks(pet_name='whiskers') [case-insensitive]:
  ╭────────┬──────────┬───────────────────────┬───────┬────────────╮
  │ Time   │ Pet      │ Task                  │   Min │ Priority   │
  ├────────┼──────────┼───────────────────────┼───────┼────────────┤
  │ 18:00  │ Whiskers │ 🎾 Laser pointer play │    15 │ 🟢 Low     │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  ╰────────┴──────────┴───────────────────────┴───────┴────────────╯

filter_tasks(completed=True):
  ╭────────┬──────────┬───────────────────────┬───────┬────────────╮
  │ Time   │ Pet      │ Task                  │   Min │ Priority   │
  ├────────┼──────────┼───────────────────────┼───────┼────────────┤
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  ╰────────┴──────────┴───────────────────────┴───────┴────────────╯

filter_tasks(completed=False):
  ╭────────┬──────────┬───────────────────────┬───────┬────────────╮
  │ Time   │ Pet      │ Task                  │   Min │ Priority   │
  ├────────┼──────────┼───────────────────────┼───────┼────────────┤
  │ 17:30  │ Buddy    │ 🍖 Evening feeding    │    10 │ 🟡 Medium  │
  │ --:--  │ Buddy    │ 🧼 Brush coat         │    10 │ 🟢 Low     │
  │ 07:30  │ Buddy    │ 🦮 Morning walk       │    30 │ 🔴 High    │
  │ 06:30  │ Buddy    │ 🍖 Early snack        │     5 │ 🟢 Low     │
  │ 18:00  │ Whiskers │ 🎾 Laser pointer play │    15 │ 🟢 Low     │
  │ 08:00  │ Whiskers │ 💊 Thyroid medication │     5 │ 🔴 High    │
  ╰────────┴──────────┴───────────────────────┴───────┴────────────╯

sort_by_time(filter_tasks(completed=False, pet_name='Buddy')):
  ╭────────┬───────┬────────────────────┬───────┬────────────╮
  │ Time   │ Pet   │ Task               │   Min │ Priority   │
  ├────────┼───────┼────────────────────┼───────┼────────────┤
  │ 06:30  │ Buddy │ 🍖 Early snack     │     5 │ 🟢 Low     │
  │ 07:30  │ Buddy │ 🦮 Morning walk    │    30 │ 🔴 High    │
  │ 17:30  │ Buddy │ 🍖 Evening feeding │    10 │ 🟡 Medium  │
  │ --:--  │ Buddy │ 🧼 Brush coat      │    10 │ 🟢 Low     │
  ╰────────┴───────┴────────────────────┴───────┴────────────╯

========================================================
 🚨 Conflict check
========================================================
  ⚠  Conflict: Buddy's 'Flea treatment' (09:00-09:10) overlaps Whiskers' 'Nail trim' (09:00-09:10)
  ⚠  Conflict for Buddy: 'Evening feeding' (17:30-17:40) overlaps 'Vet call' (17:35-17:50)
  ⚠  Conflict: Buddy's 'Training' (18:00-18:20) overlaps Whiskers' 'Laser pointer play' (18:00-18:15)
  ⚠  Conflict: Buddy's 'Training' (18:00-18:20) overlaps Whiskers' 'Brush fur' (18:05-18:15)
  ⚠  Conflict for Whiskers: 'Laser pointer play' (18:00-18:15) overlaps 'Brush fur' (18:05-18:15)

  Same-time check (Flea treatment vs Nail trim at 09:00): ✅ PASS

========================================================
 📅 Today's Schedule for Jordan (2026-10-17)
========================================================

  ╭────────┬──────────┬───────────────────────┬───────┬────────────┬──────────────────────────────────────────────────────────────────────────────╮
  │ Time   │ Pet      │ Task                  │   Min │ Priority   │ Why                                                                          │
  ├────────┼──────────┼───────────────────────┼───────┼────────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ 09:00  │ Buddy    │ 🧼 Flea treatment     │    10 │ 🟡 Medium  │ Medium priority, scheduled at preferred time 09:00                           │
  │ 09:10  │ Whiskers │ 🧼 Nail trim          │    10 │ 🟡 Medium  │ Medium priority, preferred time not available so used the earliest free slot │
  │ 09:20  │ Buddy    │ 🍖 Early snack        │     5 │ 🟢 Low     │ Low priority, preferred time not available so used the earliest free slot    │
  │ 09:25  │ Buddy    │ 🧼 Brush coat         │    10 │ 🟢 Low     │ Low priority                                                                 │
  │ 17:30  │ Buddy    │ 🍖 Evening feeding    │    10 │ 🟡 Medium  │ Medium priority, scheduled at preferred time 17:30                           │
  │ 17:40  │ Buddy    │ 🧼 Vet call           │    15 │ 🟡 Medium  │ Medium priority, preferred time not available so used the earliest free slot │
  │ 18:00  │ Whiskers │ 🎾 Laser pointer play │    15 │ 🟢 Low     │ Low priority, scheduled at preferred time 18:00                              │
  │ 18:15  │ Buddy    │ 🎾 Training           │    20 │ 🟢 Low     │ Low priority, preferred time not available so used the earliest free slot    │
  │ 18:35  │ Whiskers │ 🧼 Brush fur          │    10 │ 🟢 Low     │ Low priority, preferred time not available so used the earliest free slot    │
  ╰────────┴──────────┴───────────────────────┴───────┴────────────┴──────────────────────────────────────────────────────────────────────────────╯

💤 Skipped
  ╭──────────┬───────────────────────┬─────────────────────────────────────────────╮
  │ Pet      │ Task                  │ Reason                                      │
  ├──────────┼───────────────────────┼─────────────────────────────────────────────┤
  │ Buddy    │ 🦮 Morning walk       │ Not due today (daily task, done 2026-10-17) │
  │ Buddy    │ 🦮 Morning walk       │ Not due until 2026-10-18 (daily task)       │
  │ Whiskers │ 💊 Thyroid medication │ Not due today (daily task, done 2026-10-17) │
  │ Whiskers │ 💊 Thyroid medication │ Not due until 2026-10-18 (daily task)       │
  ╰──────────┴───────────────────────┴─────────────────────────────────────────────╯

⚠  Warnings
  ⚠  Conflict: Buddy's 'Flea treatment' (09:00-09:10) overlaps Whiskers' 'Nail trim' (09:00-09:10)
  ⚠  Conflict for Buddy: 'Evening feeding' (17:30-17:40) overlaps 'Vet call' (17:35-17:50)
  ⚠  Conflict: Buddy's 'Training' (18:00-18:20) overlaps Whiskers' 'Laser pointer play' (18:00-18:15)
  ⚠  Conflict: Buddy's 'Training' (18:00-18:20) overlaps Whiskers' 'Brush fur' (18:05-18:15)
  ⚠  Conflict for Whiskers: 'Laser pointer play' (18:00-18:15) overlaps 'Brush fur' (18:05-18:15)

  ⏱  Time used: [██████████████████░░] 105/120 min
  9 scheduled, 4 skipped, 105 of 120 minutes used

========================================================
 🕒 Next available slot
========================================================
  ╭───────────────┬──────────────┬─────────────────╮
  │ Task length   │ Not before   │ Result          │
  ├───────────────┼──────────────┼─────────────────┤
  │ 15 min        │ any time     │ ✅ 07:00        │
  │ 20 min        │ 18:00        │ ❌ no free slot │
  │ 30 min        │ any time     │ ❌ no free slot │
  ╰───────────────┴──────────────┴─────────────────╯

========================================================
 🧠 Optimal planner vs greedy
========================================================

Greedy plan  (10 points)
  ╭────────┬─────────────┬───────────────╮
  │ Time   │ Task        │ Why           │
  ├────────┼─────────────┼───────────────┤
  │ 08:00  │ 🧼 Grooming │ High priority │
  ╰────────┴─────────────┴───────────────╯
  💤 Short walk 1: Not enough time today (20 min needed, 0 left)
  💤 Short walk 2: Not enough time today (20 min needed, 0 left)
  💤 Short walk 3: Not enough time today (20 min needed, 0 left)

Optimal plan  (15 points)
  ╭────────┬─────────────────┬──────────────────────────╮
  │ Time   │ Task            │ Why                      │
  ├────────┼─────────────────┼──────────────────────────┤
  │ 08:00  │ 🦮 Short walk 1 │ Medium priority (+5 pts) │
  │ 08:20  │ 🦮 Short walk 2 │ Medium priority (+5 pts) │
  │ 08:40  │ 🦮 Short walk 3 │ Medium priority (+5 pts) │
  ╰────────┴─────────────────┴──────────────────────────╯
  💤 Grooming: Skipped: the best plan with it scores 10 points, against 15 for the chosen plan

Dependencies and spacing
  ╭────────┬───────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────╮
  │ Time   │ Task          │ Why                                                                                                │
  ├────────┼───────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 07:00  │ 🍖 Breakfast  │ Medium priority (+5 pts), at preferred time 07:00                                                  │
  │ 07:15  │ 💊 Thyroid AM │ High priority (+10 pts), moved to 07:15 from 07:00 (-1 pts) because it must come after 'Breakfast' │
  │ 15:30  │ 💊 Thyroid PM │ High priority (+10 pts), moved to 15:30 from 08:00 (-30 pts)                                       │
  ╰────────┴───────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────╯

Errors
  ❌ Dependency cycle: Breakfast -> Thyroid AM -> Breakfast
  ❌ Cannot schedule must-do meds: Whiskers' 'Thyroid PM' needs 5 min but the longest time window is 3 min; Whiskers' 'Thyroid AM' needs 5 min but the longest time window is 3 min
```

</details>

## 🧪 Testing

The 59 tests in [tests/test_pawpal.py](tests/test_pawpal.py) cover `pawpal_system.py`. The Streamlit UI is not tested automatically.

```bash
python -m pytest -v                        # one line per test
python -m pytest -k "conflict"             # tests whose name matches a keyword
python -m pytest tests/test_pawpal.py::test_find_conflicts_exact_same_time_and_no_conflicts
```

| Area | What is checked |
|---|---|
| **Sorting** | `sort_by_time()` is chronological across pets, puts no-time tasks last, keeps original order for equal times, and handles empty input. `sort_tasks()` orders by priority, then time, then duration. |
| **Recurrence** | Completing a daily task creates one copy due tomorrow (weekly: in 7 days) on the same pet. The copy is skipped today and becomes due on its date. Repeated completion never creates extra copies. |
| **Conflicts** | Same-time tasks are flagged for one pet or several, and every pair is reported when three or more collide. Back-to-back and no-time tasks are not flagged. Warnings never stop scheduling. |
| **Plan generation** | Preferred times are used when free. Tasks are skipped, with a reason, when not due, out of minutes, or no window has room. Scheduled tasks never overlap. |
| **Optimal planner** | Optimal beats greedy where greedy takes one big high-priority task, and never scores lower without extra constraints. Dependency cycles raise an error with the path. Dependencies move tasks and explain it. Meds keep an 8-hour gap. A must-do task that cannot fit raises a clear error. Empty input and zero free time give an empty plan. |
| **Slots and priority sort** | `find_next_available_slot()` skips busy time and respects the earliest time, window ends and remaining minutes. `sort_by_priority()` orders by priority then time and works on a copy. |
| **Models and filtering** | Pet/task and owner/pet links stay in sync, duplicates are ignored, errors are raised for tasks or pets that don't belong, and `filter_tasks()` works by completion and pet name. |

**Confidence: ★★★★☆ (4 of 5).** All tests pass and they cover the behaviors that matter most. It is not 5 stars because some edge cases are not tested yet.

## 📁 Project files

| File | Purpose |
|---|---|
| [app.py](app.py) | Streamlit UI |
| [pawpal_system.py](pawpal_system.py) | Models and scheduling logic |
| [requirements.txt](requirements.txt) | Dependencies: streamlit, pytest, tabulate, wcwidth |
| [main.py](main.py) | Scripted CLI demo, with the tabulate/emoji/color formatting |
| [tests/](tests/) | Automated tests |
| [diagrams/](diagrams/) | UML class diagrams |
| [reflection.md](reflection.md) | Design reflection |
| [ai_interactions.md](ai_interactions.md) | Notes on AI use |
