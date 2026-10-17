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

    buddy.add_task(Task("Morning walk", "walk", 30, "high", "daily", time(7, 30)))
    buddy.add_task(Task("Evening feeding", "feeding", 10, "medium", "daily", time(17, 30)))
    whiskers.add_task(Task("Thyroid medication", "meds", 5, "high", "daily", time(8, 0)))
    whiskers.add_task(Task("Laser pointer play", "enrichment", 15, "low", "daily", time(18, 0)))

    scheduler = Scheduler(owner)
    plan = scheduler.generate_plan()

    print("=" * 40)
    print("Today's Schedule")
    print("=" * 40)
    print(plan.display())
    print("-" * 40)
    print(plan.summary())


if __name__ == "__main__":
    main()
