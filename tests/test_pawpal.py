import os
import sys
from datetime import date, time, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import (  # noqa: E402
    DailyPlan,
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
