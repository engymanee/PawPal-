import os
import sys
from datetime import date, time, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import (  # noqa: E402
    DailyPlan,
    DependencyCycleError,
    MustDoError,
    Owner,
    Pet,
    Scheduler,
    Task,
    TimeWindow,
)


def make_task(title="Walk", priority="medium", duration=30, frequency="daily", preferred=None):
    return Task(title, "walk", duration, priority, frequency, preferred_time=preferred)


def make_pet(name="Rex"):
    return Pet(name, "dog", "lab", 3, "none")


def make_owner(minutes=120, windows=None):
    return Owner("Sam", minutes, time_windows=windows or [])


# ---- TimeWindow ----

def test_time_window_duration_and_contains():
    w = TimeWindow(time(9, 0), time(10, 30))
    assert w.duration_minutes() == 90
    assert w.contains(time(9, 0))
    assert not w.contains(time(10, 30))


# ---- Task ----

def test_mark_complete_sets_today():
    t = make_task()
    t.mark_complete()
    assert t.last_completed == date.today()


def test_is_due_today_rules():
    t = make_task(frequency="daily")
    assert t.is_due_today()
    t.mark_complete()
    assert not t.is_due_today()
    t.last_completed = date.today() - timedelta(days=1)
    assert t.is_due_today()

    w = make_task(frequency="weekly")
    w.last_completed = date.today() - timedelta(days=6)
    assert not w.is_due_today()
    w.last_completed = date.today() - timedelta(days=7)
    assert w.is_due_today()


@pytest.mark.parametrize("frequency, days", [("daily", 1), ("weekly", 7)])
def test_mark_complete_creates_next_occurrence(frequency, days):
    pet = make_pet()
    task = make_task("Walk", "high", 30, frequency, preferred=time(8))
    pet.add_task(task)

    nxt = task.mark_complete()

    assert nxt is not None and nxt is not task
    assert nxt.due_date == date.today() + timedelta(days=days)
    assert (nxt.title, nxt.duration_minutes, nxt.priority, nxt.frequency, nxt.preferred_time) == (
        "Walk", 30, "high", frequency, time(8)
    )
    assert nxt.last_completed is None
    assert nxt.pet is pet and nxt in pet.tasks and len(pet.tasks) == 2
    assert task.next_occurrence is nxt


def test_next_occurrence_not_due_until_its_date():
    pet = make_pet()
    task = make_task()
    pet.add_task(task)
    nxt = task.mark_complete()
    assert not task.is_due_today()  # the completed one is finished
    assert not nxt.is_due_today()  # the new one waits for tomorrow
    nxt.due_date = date.today()
    assert nxt.is_due_today()


def test_mark_complete_twice_creates_only_one_successor():
    pet = make_pet()
    task = make_task()
    pet.add_task(task)
    first = task.mark_complete()
    assert task.mark_complete() is first
    assert len(pet.tasks) == 2


def test_mark_complete_without_pet_creates_nothing():
    assert make_task().mark_complete() is None


def test_plan_skips_future_occurrence_with_due_date_reason():
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    task = make_task("Walk")
    pet.add_task(task)
    task.mark_complete()
    plan = Scheduler(owner).generate_plan()
    assert plan.scheduled_tasks == []
    reasons = [r for _t, r in plan.skipped_tasks]
    assert any(r.startswith(f"Not due until {(date.today() + timedelta(days=1)).isoformat()}") for r in reasons)


def test_priority_score():
    assert [make_task(priority=p).priority_score() for p in ("low", "medium", "high")] == [1, 2, 3]


# ---- Pet / Owner ----

def test_add_task_links_and_ignores_duplicate():
    pet, task = make_pet(), make_task()
    pet.add_task(task)
    pet.add_task(task)
    assert pet.tasks == [task]
    assert task.pet is pet


def test_remove_task_and_error():
    pet, task = make_pet(), make_task()
    pet.add_task(task)
    pet.remove_task(task)
    assert pet.tasks == [] and task.pet is None
    with pytest.raises(ValueError):
        pet.remove_task(task)


def test_edit_task():
    pet, task = make_pet(), make_task()
    pet.add_task(task)
    pet.edit_task(task, duration_minutes=45, priority="high")
    assert task.duration_minutes == 45 and task.priority == "high"
    with pytest.raises(AttributeError):
        pet.edit_task(task, bogus=1)
    with pytest.raises(ValueError):
        pet.edit_task(make_task(), priority="low")


def test_get_tasks_returns_copy():
    pet = make_pet()
    pet.add_task(make_task())
    pet.get_tasks().clear()
    assert len(pet.tasks) == 1


def test_owner_pets_and_all_tasks():
    owner, a, b = make_owner(), make_pet("A"), make_pet("B")
    owner.add_pet(a)
    owner.add_pet(a)
    owner.add_pet(b)
    assert len(owner.pets) == 2 and a.owner is owner
    a.add_task(make_task("t1"))
    b.add_task(make_task("t2"))
    assert {t.title for t in owner.get_all_tasks()} == {"t1", "t2"}
    owner.remove_pet(a)
    assert a.owner is None
    with pytest.raises(ValueError):
        owner.remove_pet(a)


def test_set_availability_and_preference():
    owner = make_owner()
    owner.set_availability(60, [TimeWindow(time(9), time(10))])
    assert owner.available_minutes == 60 and len(owner.time_windows) == 1
    with pytest.raises(ValueError):
        owner.set_availability(-1, [])
    owner.set_preference("walks", "morning")
    assert owner.preferences["walks"] == "morning"


# ---- DailyPlan ----

def test_daily_plan_records():
    owner = make_owner()
    plan = DailyPlan(owner, date.today())
    t1, t2 = make_task("a", duration=20), make_task("b")
    plan.add_scheduled(t1, time(9), "why a")
    plan.add_skipped(t2, "why b")
    assert plan.total_minutes_used == 20
    assert plan.get_reason(t1) == "why a"
    assert plan.get_reason(t2) == "why b"
    assert plan.get_reason(make_task("c")) is None
    with pytest.raises(ValueError):
        plan.complete_task(t2)
    plan.complete_task(t1)
    assert t1.last_completed == date.today()


# ---- Scheduler ----

def build(minutes=120, windows=None, tasks=()):
    owner = make_owner(minutes, windows)
    pet = make_pet()
    owner.add_pet(pet)
    for t in tasks:
        pet.add_task(t)
    return owner, Scheduler(owner)


def test_sort_tasks_priority_then_time_then_duration():
    low = make_task("low", "low")
    high_late = make_task("high_late", "high", preferred=time(15))
    high_early = make_task("high_early", "high", preferred=time(8))
    high_none = make_task("high_none", "high")
    _, sched = build(tasks=[low, high_none, high_late, high_early])
    assert [t.title for t in sched.sort_tasks()] == ["high_early", "high_late", "high_none", "low"]


def test_sort_by_time_orders_by_preferred_time_none_last():
    none_a = make_task("none_a", "high")
    late = make_task("late", "low", preferred=time(15))
    early = make_task("early", "low", preferred=time(8, 30))
    none_b = make_task("none_b", "low")
    _, sched = build(tasks=[none_a, late, none_b, early])
    assert [t.title for t in sched.sort_by_time()] == ["early", "late", "none_a", "none_b"]
    # Also accepts an explicit list and leaves it unchanged
    given = [late, early]
    assert sched.sort_by_time(given) == [early, late]
    assert given == [late, early]


def test_filter_tasks_by_completion_and_pet():
    owner = make_owner()
    rex, mia = make_pet("Rex"), make_pet("Mia")
    owner.add_pet(rex)
    owner.add_pet(mia)
    done = make_task("done")
    done.mark_complete()
    pending = make_task("pending")
    mia_task = make_task("mia_task")
    rex.add_task(done)
    rex.add_task(pending)
    mia.add_task(mia_task)
    sched = Scheduler(owner)

    assert sched.filter_tasks() == [done, pending, mia_task]  # no filters returns everything
    assert sched.filter_tasks(completed=True) == [done]
    assert sched.filter_tasks(completed=False) == [pending, mia_task]
    assert sched.filter_tasks(pet_name="rex") == [done, pending]  # case-insensitive
    assert sched.filter_tasks(completed=False, pet_name="Rex") == [pending]  # both filters combine
    assert sched.filter_tasks(pet_name="Nobody") == []


def test_find_conflicts_same_pet_different_pets_and_none():
    owner = make_owner()
    rex, mia = make_pet("Rex"), make_pet("Mia")
    owner.add_pet(rex)
    owner.add_pet(mia)
    rex.add_task(make_task("Walk", duration=30, preferred=time(8, 0)))
    rex.add_task(make_task("Brush", duration=10, preferred=time(8, 15)))  # overlaps Walk, same pet
    mia.add_task(make_task("Meds", duration=5, preferred=time(8, 20)))  # overlaps Brush, other pet
    mia.add_task(make_task("Play", duration=15, preferred=time(9, 0)))  # starts when Walk ends: fine
    mia.add_task(make_task("Anytime"))  # no preferred time: never conflicts
    warnings = Scheduler(owner).find_conflicts()
    assert len(warnings) == 3
    assert any(w.startswith("Conflict for Rex:") and "'Walk'" in w and "'Brush'" in w for w in warnings)
    assert any("Rex's 'Brush' (08:15-08:25)" in w and "Mia's 'Meds' (08:20-08:25)" in w for w in warnings)
    assert not any("'Play'" in w for w in warnings)


def test_find_conflicts_exact_same_time_and_no_conflicts():
    owner = make_owner()
    rex = make_pet()
    owner.add_pet(rex)
    rex.add_task(make_task("A", preferred=time(7)))
    rex.add_task(make_task("B", preferred=time(7)))
    assert len(Scheduler(owner).find_conflicts()) == 1
    assert Scheduler(make_owner()).find_conflicts() == []


def test_find_conflicts_ignores_tasks_not_due_today():
    owner = make_owner()
    rex = make_pet()
    owner.add_pet(rex)
    done = make_task("A", preferred=time(7))
    done.last_completed = date.today()
    rex.add_task(done)
    rex.add_task(make_task("B", preferred=time(7)))
    assert Scheduler(owner).find_conflicts() == []


def test_plan_carries_warnings_and_still_schedules_everything_it_can():
    owner = make_owner()
    rex = make_pet()
    owner.add_pet(rex)
    rex.add_task(make_task("A", duration=30, preferred=time(8)))
    rex.add_task(make_task("B", duration=30, preferred=time(8)))
    plan = Scheduler(owner).generate_plan()
    assert len(plan.warnings) == 1
    assert len(plan.scheduled_tasks) == 2  # one is moved, nothing crashes
    assert "Warnings:" in plan.display()


def test_generate_plan_uses_preferred_time():
    t = make_task("meds", "high", 10, preferred=time(12))
    _, sched = build(tasks=[t])
    plan = sched.generate_plan()
    assert plan.scheduled_tasks[0][1] == time(12)
    assert "preferred time" in plan.get_reason(t)


def test_generate_plan_skips_when_out_of_minutes():
    big, small = make_task("big", "high", 60), make_task("small", "low", 30)
    _, sched = build(minutes=60, tasks=[big, small])
    plan = sched.generate_plan()
    assert [t for t, _, _ in plan.scheduled_tasks] == [big]
    assert "Not enough time" in plan.get_reason(small)


def test_generate_plan_skips_not_due():
    t = make_task()
    t.mark_complete()
    _, sched = build(tasks=[t])
    plan = sched.generate_plan()
    assert plan.scheduled_tasks == []
    assert "Not due today" in plan.get_reason(t)


def test_generate_plan_skips_when_window_too_small():
    t = make_task(duration=60)
    _, sched = build(windows=[TimeWindow(time(9), time(9, 30))], tasks=[t])
    plan = sched.generate_plan()
    assert "No time window" in plan.get_reason(t)


def test_tasks_do_not_overlap():
    tasks = [make_task(f"t{i}", duration=30) for i in range(3)]
    _, sched = build(tasks=tasks)
    starts = sorted(s for _, s, _ in sched.generate_plan().scheduled_tasks)
    assert starts == [time(8, 0), time(8, 30), time(9, 0)]


def test_explain_choice_and_display_summary():
    t = make_task("walk")
    _, sched = build(tasks=[t])
    assert sched.explain_choice(t) == "No plan has been generated yet."
    plan = sched.generate_plan()
    assert "walk (Rex)" in sched.explain_choice(t)
    assert "was not part of the plan" in sched.explain_choice(make_task("other"))
    assert "Plan for Sam" in plan.display()
    assert plan.summary() == "1 scheduled, 0 skipped, 30 of 120 minutes used"


# ---- Simple tests ----

def test_task_completion_changes_status():
    task = make_task()
    assert task.last_completed is None
    assert task.is_due_today()
    task.mark_complete()
    assert task.last_completed == date.today()
    assert not task.is_due_today()


def test_task_addition_increases_pet_task_count():
    pet = make_pet()
    assert len(pet.tasks) == 0
    pet.add_task(make_task("Walk"))
    assert len(pet.tasks) == 1
    pet.add_task(make_task("Feed"))
    assert len(pet.tasks) == 2


# ---- Sorting correctness: chronological order ----

def test_sort_by_time_is_chronological_across_pets_and_input_order():
    owner = make_owner()
    rex, mia = make_pet("Rex"), make_pet("Mia")
    owner.add_pet(rex)
    owner.add_pet(mia)
    evening = make_task("evening", preferred=time(18, 45))
    midnight = make_task("midnight", preferred=time(0, 0))  # falsy-looking value must still sort first
    noon = make_task("noon", preferred=time(12, 0))
    morning = make_task("morning", preferred=time(7, 5))
    rex.add_task(evening)
    mia.add_task(noon)
    rex.add_task(midnight)
    mia.add_task(morning)

    ordered = Scheduler(owner).sort_by_time()

    assert [t.title for t in ordered] == ["midnight", "morning", "noon", "evening"]
    times = [t.preferred_time for t in ordered]
    assert times == sorted(times)


def test_sort_by_time_keeps_original_order_for_equal_times():
    first = make_task("first", preferred=time(9, 0))
    second = make_task("second", preferred=time(9, 0))
    third = make_task("third", preferred=time(9, 0))
    _, sched = build(tasks=[first, second, third])
    assert sched.sort_by_time() == [first, second, third]


def test_sort_by_time_handles_empty_owner_and_empty_list():
    sched = Scheduler(make_owner())
    assert sched.sort_by_time() == []
    assert sched.sort_by_time([]) == []


# ---- Recurrence logic: completing a daily task creates tomorrow's task ----

def test_completing_daily_task_creates_task_for_following_day():
    pet = make_pet()
    task = make_task("Feed", "high", 10, "daily", preferred=time(7, 30))
    pet.add_task(task)

    new_task = task.mark_complete()

    assert new_task is not None and new_task is not task
    assert new_task.due_date == date.today() + timedelta(days=1)
    assert new_task in pet.tasks and len(pet.tasks) == 2
    assert new_task.last_completed is None
    assert (new_task.title, new_task.priority, new_task.preferred_time) == ("Feed", "high", time(7, 30))


def test_daily_recurrence_via_plan_appears_tomorrow_not_today():
    owner, sched = build(tasks=[make_task("Feed", duration=10)])
    feed = owner.get_all_tasks()[0]
    plan = sched.generate_plan()
    plan.complete_task(feed)
    new_task = feed.next_occurrence

    # Today: the new task is skipped, with its due date as the reason.
    todays = sched.generate_plan()
    assert [t for t, *_ in todays.scheduled_tasks] == []
    assert new_task in [t for t, _ in todays.skipped_tasks]
    assert (date.today() + timedelta(days=1)).isoformat() in todays.get_reason(new_task)

    # Tomorrow: once its due date arrives, it is due again.
    new_task.due_date = date.today()
    assert new_task.is_due_today()
    assert new_task in [t for t, *_ in sched.generate_plan().scheduled_tasks]


def test_daily_recurrence_does_not_pile_up_on_repeat_completion():
    pet = make_pet()
    task = make_task()
    pet.add_task(task)
    task.mark_complete()
    task.mark_complete()
    task.mark_complete()
    assert len(pet.tasks) == 2  # original plus exactly one successor


# ---- Conflict detection: duplicate times are flagged ----

def test_scheduler_flags_two_tasks_at_the_same_time_for_one_pet():
    owner = make_owner()
    rex = make_pet("Rex")
    owner.add_pet(rex)
    rex.add_task(make_task("Walk", duration=30, preferred=time(8, 0)))
    rex.add_task(make_task("Feed", duration=10, preferred=time(8, 0)))

    warnings = Scheduler(owner).find_conflicts()

    assert len(warnings) == 1
    assert warnings[0].startswith("Conflict for Rex:")
    assert "'Walk'" in warnings[0] and "'Feed'" in warnings[0]
    assert "08:00" in warnings[0]


def test_scheduler_flags_same_time_across_different_pets():
    owner = make_owner()
    rex, mia = make_pet("Rex"), make_pet("Mia")
    owner.add_pet(rex)
    owner.add_pet(mia)
    rex.add_task(make_task("Walk", preferred=time(17, 0)))
    mia.add_task(make_task("Meds", preferred=time(17, 0)))

    warnings = Scheduler(owner).find_conflicts()

    assert len(warnings) == 1
    assert "Rex's 'Walk'" in warnings[0] and "Mia's 'Meds'" in warnings[0]


def test_three_tasks_at_the_same_time_report_every_pair():
    owner = make_owner()
    rex = make_pet()
    owner.add_pet(rex)
    for name in ("A", "B", "C"):
        rex.add_task(make_task(name, preferred=time(10, 0)))
    assert len(Scheduler(owner).find_conflicts()) == 3  # A-B, A-C, B-C


def test_different_times_are_not_flagged():
    owner = make_owner()
    rex = make_pet()
    owner.add_pet(rex)
    rex.add_task(make_task("A", duration=30, preferred=time(8, 0)))
    rex.add_task(make_task("B", duration=30, preferred=time(8, 30)))  # starts as A ends
    rex.add_task(make_task("C", duration=30, preferred=time(14, 0)))
    assert Scheduler(owner).find_conflicts() == []


def test_duplicate_time_warning_reaches_the_plan_without_crashing():
    owner = make_owner()
    rex = make_pet()
    owner.add_pet(rex)
    rex.add_task(make_task("A", preferred=time(9, 0)))
    rex.add_task(make_task("B", preferred=time(9, 0)))

    plan = Scheduler(owner).generate_plan()

    assert len(plan.warnings) == 1
    starts = [start for _, start, _ in plan.scheduled_tasks]
    assert len(starts) == 2 and len(set(starts)) == 2  # both scheduled, at different times


def test_next_slot_skips_busy_time_and_finds_gap():
    owner = make_owner(minutes=300, windows=[TimeWindow(time(8, 0), time(12, 0))])
    rex = make_pet()
    owner.add_pet(rex)
    rex.add_task(make_task("A", duration=60, preferred=time(8, 0)))
    rex.add_task(make_task("B", duration=60, preferred=time(10, 0)))
    s = Scheduler(owner)
    assert s.find_next_available_slot(60) == time(9, 0)  # gap between A and B
    assert s.find_next_available_slot(90) is None  # no gap that long: 9-10 and 11-12 are 60 each


def test_next_slot_respects_earliest_and_window_end():
    owner = make_owner(minutes=300, windows=[TimeWindow(time(8, 0), time(12, 0))])
    rex = make_pet()
    owner.add_pet(rex)
    rex.add_task(make_task("A", duration=60, preferred=time(8, 0)))
    s = Scheduler(owner)
    assert s.find_next_available_slot(30, earliest=time(10, 0)) == time(10, 0)
    assert s.find_next_available_slot(30, earliest=time(11, 45)) is None


def test_next_slot_none_when_owner_out_of_minutes():
    owner = make_owner(minutes=60)
    rex = make_pet()
    owner.add_pet(rex)
    rex.add_task(make_task("A", duration=60, preferred=time(8, 0)))
    assert Scheduler(owner).find_next_available_slot(15) is None


def test_next_slot_rejects_nonpositive_duration():
    with pytest.raises(ValueError):
        Scheduler(make_owner()).find_next_available_slot(0)


def test_sort_by_priority_then_time():
    owner = make_owner()
    rex = make_pet()
    owner.add_pet(rex)
    low_early = make_task("low_early", priority="low", preferred=time(7, 0))
    high_late = make_task("high_late", priority="high", preferred=time(18, 0))
    high_early = make_task("high_early", priority="high", preferred=time(9, 0))
    med_none = make_task("med_none", priority="medium")
    for t in (low_early, high_late, med_none, high_early):
        rex.add_task(t)

    titles = [t.title for t in Scheduler(owner).sort_by_priority()]

    assert titles == ["high_early", "high_late", "med_none", "low_early"]


def test_sort_by_priority_accepts_a_subset_without_changing_it():
    owner = make_owner()
    a, b = make_task("a", priority="low"), make_task("b", priority="high")
    subset = [a, b]
    assert Scheduler(owner).sort_by_priority(subset) == [b, a]
    assert subset == [a, b]


# ---- optimal_plan: constraint-based planning ----

def opt_task(title, category="walk", duration=30, priority="medium", preferred=None, depends_on=None, gap=None):
    t = Task(title, category, duration, priority, "daily", preferred_time=preferred)
    t.depends_on = depends_on or []
    t.min_gap_minutes = gap
    return t


def opt_setup(tasks, windows, minutes=600):
    owner = Owner("Sam", minutes, time_windows=windows)
    pet = make_pet()
    owner.add_pet(pet)
    for t in tasks:
        pet.add_task(t)
    return owner, Scheduler(owner)


def test_optimal_beats_greedy_when_greedy_takes_one_big_high_priority_task():
    walks = [opt_task(f"Walk {i}", duration=20, priority="medium") for i in range(3)]
    grooming = opt_task("Grooming", category="grooming", duration=60, priority="high")
    owner, sched = opt_setup([grooming] + walks, [TimeWindow(time(8, 0), time(9, 0))], minutes=60)

    greedy = sched.generate_plan()
    optimal = sched.optimal_plan()

    assert [t.title for t, _, _ in greedy.scheduled_tasks] == ["Grooming"]
    assert sched.plan_score(greedy) == 10
    assert sched.plan_score(optimal) == 15
    assert {t.title for t, _, _ in optimal.scheduled_tasks} == {"Walk 0", "Walk 1", "Walk 2"}
    reason = optimal.get_reason(grooming)
    assert "Skipped" in reason and "15" in reason  # names the scores that beat it


def test_optimal_never_scores_below_greedy_without_extra_constraints():
    owner, sched = opt_setup(
        [
            opt_task("A", duration=45, priority="high", preferred=time(8, 0)),
            opt_task("B", duration=30, priority="medium", preferred=time(8, 30)),
            opt_task("C", duration=30, priority="medium"),
            opt_task("D", duration=15, priority="low", preferred=time(9, 0)),
        ],
        [TimeWindow(time(8, 0), time(10, 0))],
        minutes=100,
    )
    assert sched.plan_score(sched.optimal_plan()) >= sched.plan_score(sched.generate_plan())


def test_dependency_cycle_raises_with_the_path():
    owner, sched = opt_setup(
        [opt_task("A", depends_on=["B"]), opt_task("B", depends_on=["A"])],
        [TimeWindow(time(8, 0), time(12, 0))],
    )
    with pytest.raises(DependencyCycleError, match="->") as err:
        sched.optimal_plan()
    assert "A" in str(err.value) and "B" in str(err.value)


def test_order_by_dependencies_puts_prerequisites_first_and_rejects_unknown_titles():
    meds = opt_task("Meds", category="meds", depends_on=["Feed"])
    feed = opt_task("Feed", category="feeding")
    owner, sched = opt_setup([meds, feed], [TimeWindow(time(8, 0), time(12, 0))])
    assert [t.title for t in sched.order_by_dependencies()] == ["Feed", "Meds"]
    meds.depends_on = ["Nope"]
    with pytest.raises(ValueError, match="Nope"):
        sched.order_by_dependencies()


def test_dependency_moves_a_task_and_explains_why():
    feed = opt_task("Feed", category="feeding", duration=30, preferred=time(8, 0))
    meds = opt_task("Meds", category="meds", duration=10, priority="high", preferred=time(8, 0), depends_on=["Feed"])
    owner, sched = opt_setup([meds, feed], [TimeWindow(time(8, 0), time(10, 0))])

    plan = sched.optimal_plan()
    starts = {t.title: start for t, start, _ in plan.scheduled_tasks}

    assert starts["Feed"] == time(8, 0)
    assert starts["Meds"] >= time(8, 30)
    assert "because it must come after 'Feed'" in plan.get_reason(meds)


def test_task_is_skipped_when_its_dependency_is_skipped():
    big = opt_task("Big", duration=200, priority="low")
    after = opt_task("After", depends_on=["Big"], priority="high")
    owner, sched = opt_setup([big, after], [TimeWindow(time(8, 0), time(9, 0))], minutes=60)
    plan = sched.optimal_plan()
    assert plan.scheduled_tasks == []
    assert "depends on 'Big'" in plan.get_reason(after)


def test_meds_keep_the_minimum_gap():
    morning = opt_task("Meds AM", category="meds", duration=10, priority="high", preferred=time(7, 0), gap=480)
    evening = opt_task("Meds PM", category="meds", duration=10, priority="high", preferred=time(8, 0), gap=480)
    owner, sched = opt_setup(
        [morning, evening],
        [TimeWindow(time(7, 0), time(10, 0)), TimeWindow(time(15, 0), time(20, 0))],
        minutes=120,
    )
    plan = sched.optimal_plan()
    starts = sorted(60 * s.hour + s.minute for _, s, _ in plan.scheduled_tasks)
    assert len(starts) == 2
    assert starts[1] - (starts[0] + 10) >= 480


def test_must_do_that_cannot_fit_gives_a_clear_error():
    meds = opt_task("Insulin", category="meds", duration=90, priority="high")
    owner, sched = opt_setup([meds], [TimeWindow(time(8, 0), time(9, 0))])
    with pytest.raises(MustDoError, match="90 min"):
        sched.optimal_plan()


def test_must_do_is_kept_even_when_it_scores_less_than_other_tasks():
    meds = opt_task("Insulin", category="meds", duration=30, priority="high")
    walks = [opt_task(f"Walk {i}", duration=30, priority="high") for i in range(2)]
    owner, sched = opt_setup([meds] + walks, [TimeWindow(time(8, 0), time(9, 0))], minutes=60)
    titles = {t.title for t, _, _ in sched.optimal_plan().scheduled_tasks}
    assert "Insulin" in titles and len(titles) == 2


def test_empty_task_list_and_zero_free_time_give_empty_plans():
    owner, sched = opt_setup([], [TimeWindow(time(8, 0), time(9, 0))])
    assert sched.optimal_plan().scheduled_tasks == []

    walk = opt_task("Walk")
    owner, sched = opt_setup([walk], [TimeWindow(time(8, 0), time(9, 0))], minutes=0)
    plan = sched.optimal_plan()
    assert plan.scheduled_tasks == [] and len(plan.skipped_tasks) == 1
