from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task, TimeWindow


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
    print("Recurring tasks created:")
    for t in (next_dose, next_walk):
        print(f"  {t.pet.name}: {t.title} ({t.frequency}) due {t.due_date.isoformat()}")
    print()

    scheduler = Scheduler(owner)

    def show(heading: str, tasks: list) -> None:
        print(f"\n{heading}")
        if not tasks:
            print("  (none)")
        for t in tasks:
            when = t.preferred_time.strftime("%H:%M") if t.preferred_time else "--:--"
            print(f"  {when}  {t.pet.name:<9} {t.title}")

    print("=" * 40)
    print("Sorting and filtering checks")
    print("=" * 40)
    show("As added (out of order):", owner.get_all_tasks())
    show("sort_by_time():", scheduler.sort_by_time())
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

    print("find_conflicts():")
    conflicts = scheduler.find_conflicts()
    for warning in conflicts or ["(none)"]:
        print(f"  {warning}")
    same_time = [w for w in conflicts if "'Flea treatment' (09:00-09:10)" in w and "'Nail trim' (09:00-09:10)" in w]
    print(f"\nSame-time check (Flea treatment vs Nail trim at 09:00): {'PASS' if same_time else 'FAIL'}")
    print()

    plan = scheduler.generate_plan()

    print("=" * 40)
    print("Today's Schedule")
    print("=" * 40)
    print(plan.display())
    print("-" * 40)
    print(plan.summary())


if __name__ == "__main__":
    main()
