from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta
from itertools import islice
from typing import Dict, List, Literal, Optional, Tuple


PRIORITY_SCORES = {"low": 1, "medium": 2, "high": 3}

# Used when the owner has not set any time windows.
DEFAULT_WINDOW = (time(8, 0), time(20, 0))


def _to_minutes(t: time) -> int:
    """Convert a time of day to minutes since midnight."""
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    """Convert minutes since midnight back to a time of day."""
    return time(minutes // 60, minutes % 60)


def _clock(minutes: int) -> str:
    """Format minutes since midnight as an "HH:MM" string.

    Values of 1440 or more wrap past midnight, so 1470 becomes "00:30".
    """
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def _conflict_message(first: Tuple[int, int, Task], second: Tuple[int, int, Task]) -> str:
    """Build one warning line for two overlapping tasks.

    Args:
        first, second: (start, end, task) tuples, with start and end in minutes since midnight.

    Returns:
        "Conflict for <pet>: ..." when both tasks belong to the same pet, otherwise
        "Conflict: <pet>'s ... overlaps <pet>'s ..." with each task's title and HH:MM-HH:MM span.
    """
    (_, _, a), (_, _, b) = first, second

    def describe(span: Tuple[int, int, Task], with_pet: bool) -> str:
        start, end, task = span
        owner = ""
        if with_pet and task.pet:
            owner = f"{task.pet.name}' " if task.pet.name.endswith("s") else f"{task.pet.name}'s "
        return f"{owner}'{task.title}' ({_clock(start)}-{_clock(end)})"

    if a.pet is not None and a.pet is b.pet:
        return f"Conflict for {a.pet.name}: {describe(first, False)} overlaps {describe(second, False)}"
    return f"Conflict: {describe(first, True)} overlaps {describe(second, True)}"


@dataclass
class TimeWindow:
    start: time
    end: time

    def duration_minutes(self) -> int:
        """Return the length of this window in minutes."""
        # IMPLEMENT: end minus start, both as minutes since midnight
        return _to_minutes(self.end) - _to_minutes(self.start)

    def contains(self, t: time) -> bool:
        """Return True if the given time falls inside this window."""
        # IMPLEMENT: start is inclusive, end is exclusive
        return self.start <= t < self.end


@dataclass
class Task:
    title: str
    category: Literal["walk", "feeding", "meds", "enrichment", "grooming"]
    duration_minutes: int
    priority: Literal["low", "medium", "high"]
    frequency: Literal["daily", "weekly"]
    preferred_time: Optional[time] = None
    last_completed: Optional[date] = None
    # Set on auto-created recurring instances: the task is not due before this date.
    due_date: Optional[date] = None
    # The recurring instance created when this task was completed; excluded from repr/eq.
    next_occurrence: Optional[Task] = field(default=None, repr=False, compare=False)
    # Back-reference set by Pet.add_task; excluded from repr/eq to avoid cycles.
    pet: Optional[Pet] = field(default=None, repr=False, compare=False)

    def mark_complete(self) -> Optional[Task]:
        """Mark this task as completed and create the next occurrence of a recurring task.

        Sets last_completed to today. If the task belongs to a pet, a copy is added to that pet
        with due_date = today + timedelta(days=1) for daily tasks or timedelta(days=7) for weekly
        ones. Only one copy is ever created: completing the task again returns the existing one.

        Returns:
            The new (or existing) next occurrence, or None if the task has no pet to attach it to.
        """
        # Record today as the last completion date
        today = date.today()
        self.last_completed = today

        # Only one successor per task, and only if there is a pet to attach it to
        if self.next_occurrence is not None:
            return self.next_occurrence
        if self.pet is None:
            return None

        # Daily tasks come back tomorrow, weekly tasks in 7 days
        days = 1 if self.frequency == "daily" else 7
        successor = Task(
            title=self.title,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            preferred_time=self.preferred_time,
            due_date=today + timedelta(days=days),
        )
        self.pet.add_task(successor)
        self.next_occurrence = successor
        return successor

    def is_due_today(self) -> bool:
        """Return True if the task is due today.

        A task is not due if it already has a next occurrence, or if its due_date is in the
        future. Otherwise it is due when it has never been completed, or when enough days have
        passed since last_completed (1 for daily tasks, 7 for weekly ones).
        """
        # A task that already has a successor is finished; the successor carries the schedule
        if self.next_occurrence is not None:
            return False
        # Recurring instances wait for their due date
        if self.due_date is not None and self.due_date > date.today():
            return False
        # Never completed means due; otherwise compare days since last completion
        if self.last_completed is None:
            return True
        days_since = (date.today() - self.last_completed).days
        if self.frequency == "daily":
            return days_since >= 1
        return days_since >= 7  # weekly

    def priority_score(self) -> int:
        """Return a numeric score for this task's priority (higher = more urgent)."""
        # IMPLEMENT: look the priority up in the score table (low=1, medium=2, high=3)
        return PRIORITY_SCORES[self.priority]


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age: int
    special_needs: str
    tasks: List[Task] = field(default_factory=list)
    # Back-reference set by Owner.add_pet; excluded from repr/eq to avoid cycles.
    owner: Optional[Owner] = field(default=None, repr=False, compare=False)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet and set task.pet to this pet."""
        # IMPLEMENT: skip duplicates (same object), then link both directions
        if any(t is task for t in self.tasks):
            return
        self.tasks.append(task)
        task.pet = self

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        # IMPLEMENT: find the task by identity, remove it, and clear its back-reference
        for i, t in enumerate(self.tasks):
            if t is task:
                del self.tasks[i]
                task.pet = None
                return
        raise ValueError(f"{task.title!r} is not one of {self.name}'s tasks")

    def edit_task(self, task: Task, **changes) -> None:
        """Update fields of an existing task."""
        # IMPLEMENT: check the task belongs to this pet, then set each changed field
        if not any(t is task for t in self.tasks):
            raise ValueError(f"{task.title!r} is not one of {self.name}'s tasks")
        for key, value in changes.items():
            if key == "pet" or not hasattr(task, key):
                raise AttributeError(f"Task has no editable field {key!r}")
            setattr(task, key, value)

    def get_tasks(self) -> List[Task]:
        """Return all of this pet's tasks."""
        # IMPLEMENT: return a copy so callers can't change the list by accident
        return list(self.tasks)


@dataclass
class Owner:
    name: str
    available_minutes: int
    time_windows: List[TimeWindow] = field(default_factory=list)
    preferences: Dict = field(default_factory=dict)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner and set pet.owner to this owner."""
        # IMPLEMENT: skip duplicates (same object), then link both directions
        if any(p is pet for p in self.pets):
            return
        self.pets.append(pet)
        pet.owner = self

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        # IMPLEMENT: find the pet by identity, remove it, and clear its back-reference
        for i, p in enumerate(self.pets):
            if p is pet:
                del self.pets[i]
                pet.owner = None
                return
        raise ValueError(f"{pet.name} is not one of {self.name}'s pets")

    def set_availability(self, minutes: int, windows: List[TimeWindow]) -> None:
        """Set total available minutes and the time windows."""
        # IMPLEMENT: reject negative minutes, then store both values
        if minutes < 0:
            raise ValueError("available minutes cannot be negative")
        self.available_minutes = minutes
        self.time_windows = list(windows)

    def set_preference(self, key: str, value) -> None:
        """Store a scheduling preference."""
        # IMPLEMENT: save the value under its key
        self.preferences[key] = value

    def get_all_tasks(self) -> List[Task]:
        """Return every task across all of the owner's pets (each task knows its pet)."""
        # IMPLEMENT: flatten each pet's task list into one list
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class DailyPlan:
    owner: Owner
    plan_date: date
    scheduled_tasks: List[Tuple[Task, time, str]] = field(default_factory=list)
    skipped_tasks: List[Tuple[Task, str]] = field(default_factory=list)
    total_minutes_used: int = 0
    warnings: List[str] = field(default_factory=list)

    def add_scheduled(self, task: Task, start: time, reason: str) -> None:
        """Record a task scheduled at a start time, with the reason it was chosen."""
        # IMPLEMENT: store the entry and add the task's duration to the minutes used
        self.scheduled_tasks.append((task, start, reason))
        self.total_minutes_used += task.duration_minutes

    def add_skipped(self, task: Task, reason: str) -> None:
        """Record a task that could not be scheduled, with the reason."""
        # IMPLEMENT: store the entry; skipped tasks use no minutes
        self.skipped_tasks.append((task, reason))

    def get_reason(self, task: Task) -> Optional[str]:
        """Return the recorded reason this task was scheduled or skipped, if any."""
        # IMPLEMENT: search scheduled entries first, then skipped ones, matching by identity
        for t, _start, reason in self.scheduled_tasks:
            if t is task:
                return reason
        for t, reason in self.skipped_tasks:
            if t is task:
                return reason
        return None

    def complete_task(self, task: Task) -> None:
        """Mark a scheduled task done by calling task.mark_complete()."""
        # IMPLEMENT: only tasks in this plan's scheduled list can be completed
        if not any(t is task for t, _start, _reason in self.scheduled_tasks):
            raise ValueError(f"{task.title!r} is not scheduled in this plan")
        task.mark_complete()

    def display(self) -> str:
        """Return the full plan formatted for display, grouped by pet."""
        # IMPLEMENT: build text lines: header, scheduled tasks per pet (by start time), then skipped tasks
        lines = [f"Plan for {self.owner.name} on {self.plan_date.isoformat()}"]

        # Group scheduled tasks by pet name
        by_pet: Dict[str, list] = {}
        for task, start, reason in sorted(self.scheduled_tasks, key=lambda e: e[1]):
            pet_name = task.pet.name if task.pet else "Unassigned"
            by_pet.setdefault(pet_name, []).append((task, start, reason))

        lines.append("Scheduled:")
        if not by_pet:
            lines.append("  (nothing scheduled)")
        for pet_name, entries in by_pet.items():
            lines.append(f"  {pet_name}:")
            for task, start, reason in entries:
                lines.append(
                    f"    {start.strftime('%H:%M')} - {task.title} "
                    f"({task.duration_minutes} min) - {reason}"
                )

        # List skipped tasks with the reason they were left out
        if self.skipped_tasks:
            lines.append("Skipped:")
            for task, reason in self.skipped_tasks:
                pet_name = task.pet.name if task.pet else "Unassigned"
                lines.append(f"  {pet_name}: {task.title} - {reason}")

        # Show any conflict warnings last
        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  {warning}")

        return "\n".join(lines)

    def summary(self) -> str:
        """Return a short summary of the plan."""
        # IMPLEMENT: one line with counts and minutes used out of the owner's available time
        return (
            f"{len(self.scheduled_tasks)} scheduled, {len(self.skipped_tasks)} skipped, "
            f"{self.total_minutes_used} of {self.owner.available_minutes} minutes used"
        )


class Scheduler:
    def __init__(self, owner: Owner):
        """Create a scheduler for the given owner, with no plan generated yet."""
        self.owner = owner
        self.plan: Optional[DailyPlan] = None

    def generate_plan(self) -> DailyPlan:
        """Build a DailyPlan from the owner's tasks and time windows, store it in self.plan, and return it."""
        # IMPLEMENT: walk the sorted tasks, place each one in a window, record why
        plan = DailyPlan(owner=self.owner, plan_date=date.today())
        plan.warnings = self.find_conflicts()
        remaining = self.owner.available_minutes

        # Set up the windows (default window if the owner gave none); cursor = next free minute in each
        windows = self.owner.time_windows or [TimeWindow(*DEFAULT_WINDOW)]
        windows = sorted(windows, key=lambda w: w.start)
        cursors = [_to_minutes(w.start) for w in windows]

        for task in self.sort_tasks():
            # Skip tasks that are not due today
            if not task.is_due_today():
                if task.due_date is not None and task.due_date > date.today():
                    reason = f"Not due until {task.due_date.isoformat()} ({task.frequency} task)"
                elif task.last_completed is None:
                    reason = f"Not due today ({task.frequency} task)"
                else:
                    reason = f"Not due today ({task.frequency} task, done {task.last_completed})"
                plan.add_skipped(task, reason)
                continue

            # Skip tasks that don't fit in the owner's remaining minutes
            if not self.fits_in_time(task, remaining):
                plan.add_skipped(
                    task,
                    f"Not enough time today ({task.duration_minutes} min needed, {remaining} left)",
                )
                continue

            # Find a start time: preferred time first, otherwise the earliest free slot
            placement = self._find_slot(task, windows, cursors)
            if placement is None:
                plan.add_skipped(task, "No time window has enough free room left")
                continue

            index, start, used_preferred = placement
            cursors[index] = start + task.duration_minutes
            remaining -= task.duration_minutes

            reason = f"{task.priority.capitalize()} priority"
            if used_preferred:
                reason += f", scheduled at preferred time {task.preferred_time.strftime('%H:%M')}"
            elif task.preferred_time is not None:
                reason += ", preferred time not available so used the earliest free slot"
            plan.add_scheduled(task, _to_time(start), reason)

        self.plan = plan
        return plan

    def _find_slot(self, task: Task, windows: List[TimeWindow], cursors: List[int]):
        """Return (window index, start minute, used_preferred) for the task, or None if nothing fits."""
        # IMPLEMENT: try the preferred time first, then fall back to the earliest window with room
        duration = task.duration_minutes

        if task.preferred_time is not None:
            preferred = _to_minutes(task.preferred_time)
            for i, w in enumerate(windows):
                start = max(cursors[i], preferred)
                if w.contains(task.preferred_time) and start + duration <= _to_minutes(w.end):
                    return i, start, start == preferred

        for i, w in enumerate(windows):
            if cursors[i] + duration <= _to_minutes(w.end):
                return i, cursors[i], False
        return None

    def sort_tasks(self) -> List[Task]:
        """Return the owner's tasks ordered by scheduling priority."""
        # IMPLEMENT: highest priority first, then earliest preferred time (none last), then shortest
        def sort_key(task: Task):
            has_time = task.preferred_time is not None
            minutes = _to_minutes(task.preferred_time) if has_time else 0
            return (-task.priority_score(), not has_time, minutes, task.duration_minutes)

        return sorted(self.owner.get_all_tasks(), key=sort_key)

    def sort_by_time(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        """Return tasks ordered by preferred time, earliest first.

        Tasks without a preferred time go last, and tasks with the same time keep their
        original order. The input list is not changed.

        Args:
            tasks: The tasks to sort. Defaults to all of the owner's tasks.

        Returns:
            A new sorted list of tasks.
        """
        # Defaults to all of the owner's tasks; sorted() is stable so equal times keep their order
        if tasks is None:
            tasks = self.owner.get_all_tasks()
        return sorted(
            tasks,
            key=lambda t: (t.preferred_time is None, _to_minutes(t.preferred_time) if t.preferred_time else 0),
        )

    def find_conflicts(self, tasks: Optional[List[Task]] = None) -> List[str]:
        """Return a warning message for each pair of tasks whose preferred times overlap.

        Each task occupies the range from its preferred time to that time plus its duration.
        Two tasks conflict if their ranges overlap, whether they are for the same pet or
        different pets. A task that starts exactly when another ends is not a conflict, and
        tasks without a preferred time are ignored. This only reports problems and never
        raises an error. Tasks are sorted by start time, so each one is compared only with
        the tasks that start before it ends.

        Args:
            tasks: The tasks to check. Defaults to the owner's tasks that are due today.

        Returns:
            A list of warning strings, empty if there are no conflicts.
        """
        # Lightweight check: only reports, never raises. Same pet or different pets both count,
        # since one owner can't do two things at once. Defaults to tasks due today.
        if tasks is None:
            tasks = [t for t in self.owner.get_all_tasks() if t.is_due_today()]

        # (start, end, task) in minutes, computed once, earliest start first
        spans = []
        for t in tasks:
            if t.preferred_time is not None:
                start = _to_minutes(t.preferred_time)
                spans.append((start, start + t.duration_minutes, t))
        spans.sort(key=lambda span: span[0])

        warnings = []
        for i, first in enumerate(spans):
            for second in islice(spans, i + 1, None):
                if second[0] >= first[1]:
                    break  # sorted by start, so nothing later can overlap first either
                warnings.append(_conflict_message(first, second))
        return warnings

    def filter_tasks(
        self, completed: Optional[bool] = None, pet_name: Optional[str] = None
    ) -> List[Task]:
        """Return the owner's tasks that match the given filters.

        A task counts as completed if it has been completed and is not due again yet.
        Filters left as None are not applied, and when both are given a task must match both.

        Args:
            completed: True for completed tasks, False for the rest, None for either.
            pet_name: Only tasks for the pet with this name. The match ignores case.

        Returns:
            A list of matching tasks in the owner's original order.
        """
        # A task counts as completed when it has been done and is not due again yet
        # None means "don't filter on this"; pet names match ignoring case
        tasks = self.owner.get_all_tasks()
        if completed is not None:
            tasks = [
                t for t in tasks if (t.last_completed is not None and not t.is_due_today()) == completed
            ]
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet and t.pet.name.lower() == pet_name.strip().lower()]
        return tasks

    def fits_in_time(self, task: Task, remaining_minutes: int) -> bool:
        """Return True if the task fits in the remaining minutes."""
        # IMPLEMENT: simple comparison
        return task.duration_minutes <= remaining_minutes

    def explain_choice(self, task: Task) -> str:
        """Return a human-readable explanation of why a task was scheduled or skipped, using self.plan."""
        # IMPLEMENT: look the reason up in the saved plan and word it for the owner
        if self.plan is None:
            return "No plan has been generated yet."
        reason = self.plan.get_reason(task)
        pet_name = task.pet.name if task.pet else "Unassigned"
        if reason is None:
            return f"{task.title} ({pet_name}) was not part of the plan."
        return f"{task.title} ({pet_name}): {reason}"
