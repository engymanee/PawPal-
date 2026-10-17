import os
import sys
from datetime import time

from tabulate import tabulate

from pawpal_system import DependencyCycleError, MustDoError, Owner, Pet, Scheduler, Task, TimeWindow

# Colors are skipped when output is piped or redirected, or when NO_COLOR is set.
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ
ANSI = {"red": "31", "yellow": "33", "green": "32", "cyan": "36", "bold": "1", "dim": "2"}

CATEGORY_ICONS = {"walk": "🦮", "feeding": "🍖", "meds": "💊", "enrichment": "🎾", "grooming": "🧼"}
PRIORITY_STYLE = {"high": ("🔴", "red"), "medium": ("🟡", "yellow"), "low": ("🟢", "green")}


def paint(text: str, style: str) -> str:
    """Wrap text in an ANSI color/style when color is enabled."""
    return f"\033[{ANSI[style]}m{text}\033[0m" if USE_COLOR else text


def priority_label(task: Task) -> str:
    """Priority with a colored dot, e.g. "🔴 High"."""
    icon, color = PRIORITY_STYLE[task.priority]
    return f"{icon} {paint(task.priority.capitalize(), color)}"


def task_label(task: Task) -> str:
    """Task title with an emoji for its category."""
    return f"{CATEGORY_ICONS[task.category]} {task.title}"


def table(rows: list, headers: list) -> None:
    """Print rows as a rounded grid, indented two spaces."""
    text = tabulate(rows, headers=headers, tablefmt="rounded_outline")
    print("\n".join("  " + line for line in text.splitlines()))


def banner(title: str) -> None:
    """Print a section heading."""
    print(paint("=" * 56, "cyan"))
    print(paint(f" {title}", "bold"))
    print(paint("=" * 56, "cyan"))


def main() -> None:
    owner = Owner(
        name="Jordan",
        available_minutes=120,
        time_windows=[
            TimeWindow(time(7, 0), time(10, 0)),
            TimeWindow(time(17, 0), time(20, 0)),
        ],
    )

    buddy = Pet("Buddy", "dog", "Labrador", 4, "none")
    whiskers = Pet("Whiskers", "cat", "Siamese", 7, "needs daily thyroid medication")
    owner.add_pet(buddy)
    owner.add_pet(whiskers)

    # Tasks are added deliberately out of time order (and across pets) to exercise the sorting
    buddy.add_task(Task("Evening feeding", "feeding", 10, "medium", "daily", time(17, 30)))
    whiskers.add_task(Task("Laser pointer play", "enrichment", 15, "low", "daily", time(18, 0)))
    buddy.add_task(Task("Brush coat", "grooming", 10, "low", "weekly"))  # no preferred time
    whiskers.add_task(Task("Thyroid medication", "meds", 5, "high", "daily", time(8, 0)))
    buddy.add_task(Task("Morning walk", "walk", 30, "high", "daily", time(7, 30)))

    # Mark one task done so the completion filter has something to find
    # Completing a task also creates the next occurrence (daily: +1 day, weekly: +7 days)
    next_dose = whiskers.tasks[1].mark_complete()  # Thyroid medication
    next_walk = buddy.tasks[2].mark_complete()  # Morning walk
    print(paint("🔁 Recurring tasks created:", "bold"))
    table(
        [[t.pet.name, task_label(t), t.frequency, t.due_date.isoformat()] for t in (next_dose, next_walk)],
        ["Pet", "Task", "Frequency", "Next due"],
    )
    print()

    # Added after the completions above (they index into the task lists)
    buddy.add_task(Task("Early snack", "feeding", 5, "low", "daily", time(6, 30)))  # earliest by time, lowest by priority

    scheduler = Scheduler(owner)

    def show(heading: str, tasks: list) -> None:
        print(f"\n{paint(heading, 'bold')}")
        if not tasks:
            print("  (none)")
            return
        table(
            [
                [t.preferred_time.strftime("%H:%M") if t.preferred_time else "--:--",
                 t.pet.name, task_label(t), t.duration_minutes, priority_label(t)]
                for t in tasks
            ],
            ["Time", "Pet", "Task", "Min", "Priority"],
        )

    banner("🔎 Sorting and filtering checks")
    show("As added (out of order):", owner.get_all_tasks())
    show("sort_by_time():", scheduler.sort_by_time())
    show("sort_by_priority() [priority first, then time]:", scheduler.sort_by_priority())
    show("filter_tasks(pet_name='Buddy'):", scheduler.filter_tasks(pet_name="Buddy"))
    show("filter_tasks(pet_name='whiskers') [case-insensitive]:", scheduler.filter_tasks(pet_name="whiskers"))
    show("filter_tasks(completed=True):", scheduler.filter_tasks(completed=True))
    show("filter_tasks(completed=False):", scheduler.filter_tasks(completed=False))
    show(
        "sort_by_time(filter_tasks(completed=False, pet_name='Buddy')):",
        scheduler.sort_by_time(scheduler.filter_tasks(completed=False, pet_name="Buddy")),
    )
    print()

    # Two tasks at overlapping times, for the same pet and for different pets
    buddy.add_task(Task("Vet call", "grooming", 15, "medium", "daily", time(17, 35)))  # overlaps Evening feeding
    whiskers.add_task(Task("Brush fur", "grooming", 10, "low", "daily", time(18, 5)))  # overlaps Laser pointer play
    buddy.add_task(Task("Training", "enrichment", 20, "low", "daily", time(18, 0)))  # overlaps Whiskers' play

    # Two tasks at exactly the same time (09:00), one per pet
    buddy.add_task(Task("Flea treatment", "grooming", 10, "medium", "daily", time(9, 0)))
    whiskers.add_task(Task("Nail trim", "grooming", 10, "medium", "daily", time(9, 0)))

    banner("🚨 Conflict check")
    conflicts = scheduler.find_conflicts()
    for warning in conflicts or ["(none)"]:
        print(f"  {paint('⚠', 'yellow')}  {warning}")
    same_time = [w for w in conflicts if "'Flea treatment' (09:00-09:10)" in w and "'Nail trim' (09:00-09:10)" in w]
    verdict = paint("✅ PASS", "green") if same_time else paint("❌ FAIL", "red")
    print(f"\n  Same-time check (Flea treatment vs Nail trim at 09:00): {verdict}")
    print()

    plan = scheduler.generate_plan()

    banner(f"📅 Today's Schedule for {owner.name} ({plan.plan_date.isoformat()})")
    print()
    table(
        [
            [start.strftime("%H:%M"), t.pet.name, task_label(t), t.duration_minutes, priority_label(t), reason]
            for t, start, reason in sorted(plan.scheduled_tasks, key=lambda e: e[1])
        ],
        ["Time", "Pet", "Task", "Min", "Priority", "Why"],
    )
    if plan.skipped_tasks:
        print(f"\n{paint('💤 Skipped', 'bold')}")
        table(
            [[t.pet.name, task_label(t), reason] for t, reason in plan.skipped_tasks],
            ["Pet", "Task", "Reason"],
        )
    if plan.warnings:
        print(f"\n{paint('⚠  Warnings', 'bold')}")
        for warning in plan.warnings:
            print(f"  {paint('⚠', 'yellow')}  {warning}")

    # Progress bar for the time budget
    used, total = plan.total_minutes_used, owner.available_minutes
    filled = round(20 * used / total) if total else 0
    color = "red" if used >= total else "yellow" if used >= 0.8 * total else "green"
    bar = paint("█" * filled, color) + paint("░" * (20 - filled), "dim")
    print(f"\n  ⏱  Time used: [{bar}] {used}/{total} min")
    print(f"  {plan.summary()}")
    print()

    banner("🕒 Next available slot")
    rows = []
    for minutes, earliest in ((15, None), (20, time(18, 0)), (30, None)):
        slot = scheduler.find_next_available_slot(minutes, earliest=earliest)
        rows.append([
            f"{minutes} min",
            earliest.strftime("%H:%M") if earliest else "any time",
            paint(f"✅ {slot.strftime('%H:%M')}", "green") if slot else paint("❌ no free slot", "red"),
        ])
    table(rows, ["Task length", "Not before", "Result"])

def optimal_demo() -> None:
    """Show the optimal planner beating the greedy one, plus its constraint errors."""
    banner("🧠 Optimal planner vs greedy")
    owner = Owner("Jordan", 60, time_windows=[TimeWindow(time(8, 0), time(9, 0))])
    rex = Pet("Rex", "dog", "Beagle", 5, "none")
    owner.add_pet(rex)
    rex.add_task(Task("Grooming", "grooming", 60, "high", "daily"))
    for i in (1, 2, 3):
        rex.add_task(Task(f"Short walk {i}", "walk", 20, "medium", "daily"))
    scheduler = Scheduler(owner)

    for name, plan in (("Greedy", scheduler.generate_plan()), ("Optimal", scheduler.optimal_plan())):
        print(f"\n{paint(f'{name} plan', 'bold')}  ({scheduler.plan_score(plan)} points)")
        table(
            [[start.strftime("%H:%M"), task_label(t), reason] for t, start, reason in plan.scheduled_tasks],
            ["Time", "Task", "Why"],
        )
        for t, reason in plan.skipped_tasks:
            print(f"  💤 {t.title}: {reason}")

    print(f"\n{paint('Dependencies and spacing', 'bold')}")
    owner = Owner("Jordan", 120, time_windows=[TimeWindow(time(7, 0), time(10, 0)), TimeWindow(time(15, 0), time(20, 0))])
    whiskers = Pet("Whiskers", "cat", "Siamese", 7, "thyroid")
    owner.add_pet(whiskers)
    feed = Task("Breakfast", "feeding", 15, "medium", "daily", time(7, 0))
    am = Task("Thyroid AM", "meds", 5, "high", "daily", time(7, 0), depends_on=["Breakfast"], min_gap_minutes=480)
    pm = Task("Thyroid PM", "meds", 5, "high", "daily", time(8, 0), min_gap_minutes=480)
    for t in (feed, am, pm):
        whiskers.add_task(t)
    plan = Scheduler(owner).optimal_plan()
    table(
        [[start.strftime("%H:%M"), task_label(t), reason] for t, start, reason in plan.scheduled_tasks],
        ["Time", "Task", "Why"],
    )

    print(f"\n{paint('Errors', 'bold')}")
    feed.depends_on = ["Thyroid AM"]  # Breakfast -> Thyroid AM -> Breakfast
    try:
        Scheduler(owner).optimal_plan()
    except DependencyCycleError as error:
        print(f"  {paint('❌', 'red')} {error}")
    feed.depends_on = []
    owner.set_availability(120, [TimeWindow(time(8, 0), time(8, 3))])  # window shorter than the meds
    try:
        Scheduler(owner).optimal_plan()
    except MustDoError as error:
        print(f"  {paint('❌', 'red')} {error}")


if __name__ == "__main__":
    main()
    print()
    optimal_demo()
