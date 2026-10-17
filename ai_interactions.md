# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**Files modified**

- `pawpal_system.py`: added `Scheduler.find_next_available_slot`
- `app.py`: added a "Find a free slot" section to the Build Schedule area, and `time` to the `datetime` import
- `tests/test_pawpal.py`: added four tests for the new method

**What task did you give the agent?**

"Add a third algorithmic capability (like 'next available slot', weighted prioritization, etc.) that goes beyond the basic requirements."

**What did the agent do?**

1. Read `pawpal_system.py`, `app.py` and the test file's helpers to see how windows, plans and cursors already worked.
2. Chose "next available slot" and wrote `find_next_available_slot(duration_minutes, earliest=None)`. It takes the owner's time windows (or the default window), subtracts the tasks in today's plan, and returns the start of the first gap that is long enough and not before `earliest`. It returns `None` if no gap fits or the owner has too few minutes left, and raises `ValueError` for a non-positive duration.
3. Added a duration input, a "Not before" time picker and a "Find slot" button to `app.py`.
4. Added tests for a gap between tasks, the `earliest` cutoff and window end, running out of minutes, and invalid durations.
5. Ran the suite: 47 passed.

**What did you have to verify or fix manually?**

- The agent's first draft of the gap test had placeholder assertions (`... if False else True`) that always passed. The agent caught this before the final run and replaced them with a real assertion (a 90-minute task returns `None` because both gaps are 60 minutes).
- The Streamlit UI was not launched by the agent, so the new widget still needs a manual check in the browser.
- The README, `reflection.md` and the UML diagrams were not updated for the new method.
- _Add your own manual corrections here, if any._

---

## Prompt Comparison (SF11) — Challenge 5: Multi-Model Prompt Comparison

> Compare two different models on the same complex algorithmic task.

**Shared prompt / task:** "Design an optimal scheduler for PawPal+ to replace the greedy `generate_plan()`. It must maximize total value (high=10, medium=5, low=2), respect the owner's time windows, lose points for each 15 minutes a task is moved from its preferred time, honor dependencies ("feed before meds"), minimum spacing ("meds 8 hours apart"), and never skip must-do high-priority meds (return an explained error instead). Say which algorithms to use and how to test it."

| | Option A: Claude (Sonnet 5.5) | Option B: Gemini |
|-|----------|----------|
| **Model / tool used** | Claude Code, in this repository | Gemini, in chat, without the code |
| **Prompt** | The shared prompt above | The shared prompt above |
| **Response summary** | A design for a branch-and-bound search in `Scheduler.optimal_plan()`. Tasks are first ordered with Kahn's algorithm, which reports the cycle path. The search then decides, task by task, to skip it or place it at a start time on a 15-minute grid inside a window. Checks: spacing, dependencies, and the remaining-minutes budget. Pruning: the current score plus the value of all undecided tasks cannot beat the best plan so far. Must-do meds are checked first and raise an error that names the conflict. Greedy and optimal plans are scored by the same function. | A problem statement and an outline: a table pairing each piece with an algorithm (0/1 knapsack to pick tasks, Kahn's topological sort for dependencies, backtracking for slots, branch and bound for speed), new `Task` fields (`depends_on`, `min_gap_minutes`), four methods to write, five tests, and example explanations. No code. It offers to write the dependency ordering first. |
| **What was useful** | It fits the existing code: it reuses `_to_minutes`, `DEFAULT_WINDOW` and `TimeWindow`, and keeps `generate_plan()` so greedy and optimal can be compared. A single score function makes "optimal is never lower than greedy" a testable claim. It spots that dependency cycles must fail before any search starts, and that the empty-plan and must-do-error cases need clear rules. | The algorithm table is a clear map of the problem. The test list is concrete, and "greedy loses, optimal wins" is a good first test. The example explanation strings ("Skipped grooming: two walks scored 20 vs. grooming 10") are the kind of output a user wants. Offering to build step by step keeps the work small. |
| **Problems noticed** | It is a design that has not been run, so the complexity claim is untested. The search is exponential in the number of tasks and needs a cap or time limit. It leaves open what happens when a task's dependency is skipped; I chose to skip the dependent too, which is a product decision. | 0/1 knapsack picks a task set from one time budget, but with windows, preferred times, spacing and ordering the set and the placement depend on each other. So the knapsack step cannot be done first, and the response does not say that. It never says how the preferred-time penalty and "moved to 7:30" interact with the search, or how skipped dependencies are handled. `depends_on` holds titles, but titles are only unique per pet in this app. It says the code "keeps `generate_plan()`" without having seen it. |
| **Decision** | Used as the base for the design. | Used for the test list and the explanation wording. |

**Which approach did you use in your final implementation and why?**

I built Claude's design as `Scheduler.optimal_plan()` and kept the greedy `generate_plan()` beside it. Claude's version was written against the real `Scheduler`, and one score function (`plan_score()`) lets both planners be compared the same way.

From Gemini's response I kept the five test cases (greedy loses and optimal wins, a dependency cycle raises an error, meds keep their gap, a must-do that cannot fit gives a clear error, empty input gives an empty plan), the new `Task` fields (`depends_on`, `min_gap_minutes`) and the style of explanation ("Skipped: the best plan with it scores 10 points, against 15 for the chosen plan"). I dropped Gemini's separate 0/1 knapsack step, because task choice and placement depend on each other here, so the search decides both together.

What changed once it was built and run:
- The search is exponential. On 14 random tasks it took about 6 seconds and hit the 200,000-step limit, so I lowered the limit to 50,000 and gave each "why was this skipped" check a smaller limit of 5,000. That brought it to about 0.4 seconds, and the plan carries a warning when the limit is reached.
- A skipped task whose dependency is skipped is skipped too, and a dependency that is not due today counts as met. Those were my choices, not part of either model's answer.
- The 59 tests pass, and `optimal_plan()` scores 15 against greedy's 10 on the grooming-versus-walks case.

**Note:** the Claude column was written in this session from the same prompt, before the code existed. The Gemini column summarizes the pasted response.
