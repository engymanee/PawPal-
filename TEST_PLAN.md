# PawPal+ Test Plan

Scope: the logic in `pawpal_system.py` (models, `Scheduler`, `DailyPlan`). The Streamlit UI (`app.py`) and `main.py` demo are out of scope except for a manual smoke check.

Status of the existing suite: `tests/test_pawpal.py` has 32 tests, all passing. This plan lists what they cover, then the gaps to fill.

## 1. Approach

- **Framework:** pytest, run with `python3 -m pytest -q`.
- **Determinism:** the code calls `date.today()`, so tests that depend on dates should freeze it (monkeypatch a `date` subclass in `pawpal_system`) or build dates relative to `date.today()`. Never hard-code calendar dates.
- **Fixtures:** one `owner` fixture with two pets and a default window. Tasks are built with a small `make_task(**overrides)` helper so each test states only what it cares about.
- **Style:** one behavior per test, with an assertion on the *reason text* as well as the outcome wherever the code produces one.
- **Priority tags:** P1 = core correctness, P2 = edge cases, P3 = hardening.

## 2. Behaviors and cases

### A. Task ordering (`sort_tasks`, `sort_by_time`)

| # | Case | Expected | Pri | Status |
|---|------|----------|-----|--------|
| A1 | Mixed priorities | high, medium, low | P1 | covered |
| A2 | Same priority, different preferred times | earlier time first, no-time last | P1 | covered |
| A3 | Same priority and time | shorter duration first | P1 | covered |
| A4 | `sort_by_time` with None times | None last, input list not mutated | P1 | covered |
| A5 | `sort_by_time` equal times | original order kept (stable) | P2 | **gap** |
| A6 | `sort_by_time(tasks=[])` and owner with no pets | returns `[]`, no error | P2 | **gap** |
| A7 | `sort_by_time` with an explicit subset | only that subset is returned | P2 | **gap** |
| A8 | Task at 00:00 vs. task with no time | 00:00 task sorts first (guards against a falsy-zero bug in the key, `if t.preferred_time`) | P2 | **gap** |

### B. Recurrence and due dates (`mark_complete`, `is_due_today`)

| # | Case | Expected | Pri | Status |
|---|------|----------|-----|--------|
| B1 | Daily complete | successor due today+1 | P1 | covered |
| B2 | Weekly complete | successor due today+7 | P1 | covered |
| B3 | Complete twice | same successor returned, pet has one copy | P1 | covered |
| B4 | No pet | returns `None`, `last_completed` still set | P1 | covered |
| B5 | Original not due after completion | `is_due_today()` is False | P1 | covered |
| B6 | Weekly boundary: completed 6 days ago vs. 7 days ago | not due / due | P1 | **gap** |
| B7 | Daily completed yesterday vs. today | due / not due | P1 | partially covered |
| B8 | `due_date` is today vs. tomorrow | due / not due | P2 | **gap** |
| B9 | Successor is itself completed | chain continues, successor-of-successor gets due_date+... from *today* (documents current behavior) | P2 | **gap** |
| B10 | `last_completed` in the future (bad data) | `days_since` negative, so not due; no crash | P3 | **gap** |
| B11 | Successor copies title, category, duration, priority, frequency, preferred_time; `last_completed` is None | all fields match | P2 | **gap** |
| B12 | Successor does not carry `next_occurrence` or `pet` from the original, but `pet` is set via `add_task` | back-reference correct | P2 | **gap** |

### C. Conflict detection (`find_conflicts`)

| # | Case | Expected | Pri | Status |
|---|------|----------|-----|--------|
| C1 | Same pet overlap | "Conflict for <pet>: ..." | P1 | covered |
| C2 | Different pets overlap | "Conflict: <pet>'s ... overlaps ..." | P1 | covered |
| C3 | Exact same start time | one conflict | P1 | covered |
| C4 | Back-to-back (end == next start) | no conflict | P1 | covered |
| C5 | Tasks with no preferred time | ignored | P1 | covered |
| C6 | Tasks not due today | excluded by default | P1 | covered |
| C7 | Three mutually overlapping tasks | exactly 3 pairs reported (verifies the early `break`) | P1 | **gap** |
| C8 | Task A overlaps B, B ends before C, A also overlaps C | pair count matches brute force | P2 | **gap** |
| C9 | Property check: for random task sets, result equals an O(n²) brute-force reference | identical pair set | P2 | **gap** |
| C10 | Pet name ending in "s" | possessive is `Max'` not `Max's` | P2 | **gap** |
| C11 | Task with no pet | message omits the owner prefix, no crash | P2 | **gap** |
| C12 | Span that crosses midnight (23:30 + 60 min) | `_clock` prints `00:30`; document that overlap with a 00:10 task is *not* detected (known limitation) | P3 | **gap** |
| C13 | Zero-duration task at the same time as another | no conflict (empty range); document the behavior | P3 | **gap** |
| C14 | Never raises, even with empty input | `[]` | P1 | covered |

### D. Plan generation (`generate_plan`, `_find_slot`)

| # | Case | Expected | Pri | Status |
|---|------|----------|-----|--------|
| D1 | Preferred time free | scheduled there; reason mentions it | P1 | covered |
| D2 | Not enough owner minutes | skipped, "Not enough time today (X min needed, Y left)" | P1 | covered |
| D3 | Not due | skipped, "Not due ..." with the right variant (never completed / completed on date / due_date) | P1 | covered (3 variants: check all) |
| D4 | Window too small | skipped, "No time window has enough free room left" | P1 | covered |
| D5 | Scheduled tasks never overlap | pairwise check across the whole plan | P1 | covered |
| D6 | No windows set | uses 08:00-20:00 default | P1 | **gap** |
| D7 | Preferred time outside every window | placed at the earliest free slot; reason "preferred time not available..." | P1 | **gap** |
| D8 | Preferred time inside a window but already occupied | pushed to after the occupant; reason says "not available" (start != preferred) | P1 | **gap** |
| D9 | Preferred time near the window end so it won't fit | falls back to the earliest slot or another window | P2 | **gap** |
| D10 | Two windows: first full, second has room | task lands in second window | P2 | **gap** |
| D11 | Unsorted windows passed in | scheduler sorts them; the first slot is in the earliest window | P2 | **gap** |
| D12 | Overlapping owner windows | no double-booked minutes (cursors are per window, so this may double-book: **likely bug, write the test first**) | P1 | **gap** |
| D13 | Overnight window (end < start) | `duration_minutes()` is negative and no slot is found; document or fix | P3 | **gap** |
| D14 | Task exactly equal to remaining minutes | scheduled, remaining becomes 0 | P2 | **gap** |
| D15 | `available_minutes == 0` | everything skipped; `summary()` reads "0 scheduled, N skipped, 0 of 0 minutes used" | P2 | **gap** |
| D16 | Zero-duration task | scheduled without moving the cursor, or rejected (decide and document) | P3 | **gap** |
| D17 | Higher-priority task is skipped for time while a lower-priority short one still fits | the low-priority one is scheduled (greedy by order, no early stop) | P2 | **gap** |
| D18 | Empty owner (no pets) | plan has nothing scheduled; `display()` shows "(nothing scheduled)" | P2 | **gap** |
| D19 | `total_minutes_used` equals the sum of scheduled durations | equal | P1 | **gap** |
| D20 | Calling `generate_plan()` twice | independent plans, the same result, `self.plan` is the latest; tasks are not mutated | P1 | **gap** |
| D21 | Conflict warnings are on the plan but the plan still schedules both tasks | covered | P1 | covered |

### E. Plan reporting (`display`, `summary`, `explain_choice`, `get_reason`)

| # | Case | Expected | Pri | Status |
|---|------|----------|-----|--------|
| E1 | `explain_choice` before any plan | "No plan has been generated yet." | P1 | covered |
| E2 | `explain_choice` for a scheduled / skipped / unknown task | reason / reason / "was not part of the plan" | P1 | covered / **gap** (unknown) |
| E3 | `display` groups by pet and sorts by start time within the whole plan | check line order | P1 | partially covered |
| E4 | `display` includes Skipped and Warnings sections only when non-empty | check absence too | P2 | **gap** |
| E5 | Task with no pet | shown under "Unassigned" | P2 | **gap** |
| E6 | `get_reason` uses identity, not equality: two equal tasks get their own reasons | each its own | P2 | **gap** |
| E7 | `complete_task` on a task not in the plan | raises `ValueError` | P1 | **gap** |
| E8 | `complete_task` on a scheduled task | sets `last_completed`, creates a successor | P1 | covered |

### F. Filtering (`filter_tasks`)

| # | Case | Expected | Pri | Status |
|---|------|----------|-----|--------|
| F1 | `completed=True` / `False` / `None` | right subsets | P1 | covered |
| F2 | `pet_name` case-insensitive | matches | P1 | covered |
| F3 | `pet_name` with surrounding whitespace | matches (the code strips the argument) | P2 | **gap** |
| F4 | Both filters together | intersection | P1 | covered |
| F5 | Unknown pet name | `[]` | P2 | **gap** |
| F6 | Completed task whose successor exists | the original counts as completed; the successor does not | P2 | **gap** |
| F7 | Task completed long enough ago to be due again | counts as *not* completed | P2 | **gap** |
| F8 | Original order preserved | order check | P2 | **gap** |

### G. Models and relationships (`Pet`, `Owner`, `TimeWindow`)

| # | Case | Expected | Pri | Status |
|---|------|----------|-----|--------|
| G1 | `add_task` / `add_pet` link both ways and ignore the same object twice | covered | P1 | covered |
| G2 | Two *equal* but distinct tasks are both added | both kept (identity, not equality) | P2 | **gap** |
| G3 | `remove_task` / `remove_pet` clear back-references | covered | P1 | covered |
| G4 | Remove something that isn't there | `ValueError` with a useful message | P1 | covered (task) / **gap** (pet) |
| G5 | `edit_task` on a foreign task | `ValueError` | P1 | covered |
| G6 | `edit_task` with an unknown field, or `pet` | `AttributeError`; the task is unchanged if the *first* key is valid and the second isn't (**partial-update risk**: the first change is applied before the error) | P2 | **gap** |
| G7 | `get_tasks` returns a copy | mutating it does not affect the pet | P1 | covered |
| G8 | `set_availability` rejects negatives; copies the windows list | covered / **gap** (copy) | P2 | partial |
| G9 | `TimeWindow.contains` is start-inclusive, end-exclusive | boundary times | P1 | covered |
| G10 | Moving a pet between owners | `owner` back-reference updates, and the old owner's list is cleaned up (**likely gap in the code**, document) | P3 | **gap** |

## 3. Known risks to probe first

These are places the code looks fragile. Writing a failing test first shows whether each is a real bug:

1. **D12, overlapping windows:** `cursors` are tracked per window, so two overlapping windows can book the same minutes.
2. **A8 / sort keys:** `if t.preferred_time` relies on `time(0, 0)` being truthy. On Python 3.5+ it is, but the guard is worth a regression test.
3. **C12 / D13, midnight:** nothing models spans past 24:00 or windows that wrap, so the behavior needs to be documented or rejected.
4. **G6, `edit_task` partial updates:** it validates keys one at a time while applying them.
5. **Staleness:** after `complete_task`, the stored plan still shows the old state and the new successor isn't in it. That is probably fine, but pin it down with a test.

## 4. Non-functional and manual checks

- **Performance smoke:** 2,000 tasks with random times must run `find_conflicts` and `generate_plan` in well under a second.
- **Manual UI smoke (`app.py`):** add an owner, two pets and tasks with overlapping times. Generate the plan and confirm the warnings and skipped reasons show. Mark a task complete and confirm the next occurrence appears.
- **Docs drift:** README examples and `diagrams/uml.mmd` still match the class and method names.

## 5. Exit criteria

- Every P1 row is covered and passing.
- Every P2 row is either passing or has a written, intentional "documented behavior" test.
- Each item in section 3 is either fixed or recorded as a known limitation in `README.md`.
- The suite runs in under 2 seconds, with no dependence on the current date or clock time.
