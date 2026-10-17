from dataclasses import dataclass, field
from datetime import date, time
from typing import Dict, List, Optional, Tuple


@dataclass
class Task:
    title: str
    category: Literal["walk", "feeding", "meds", "enrichment", "grooming"]
    duration_minutes: int
    priority: Literal["low", "medium", "high"]
     frequency: Literal["daily", "weekly"]
     preferred_time: Optional[time] = None
    last_completed: Optional[date] = None

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        raise NotImplementedError

    def is_due_today(self) -> bool:
        """Return True if the task's frequency makes it due today."""
        raise NotImplementedError

    def priority_score(self) -> int:
        """Return a numeric score for this task's priority (higher = more urgent)."""
        raise NotImplementedError


@dataclass
class Pet:
    name: str
    species: str
    breed: str
    age: int
    special_needs: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        raise NotImplementedError

    def edit_task(self, task: Task, **changes) -> None:
        """Update fields of an existing task."""
        raise NotImplementedError

    def get_tasks(self) -> List[Task]:
        """Return all of this pet's tasks."""
        raise NotImplementedError


@dataclass
class Owner:
    name: str
    available_minutes: int
    time_windows: List[Tuple[time, time]] = field(default_factory=list)
    preferences: Dict = field(default_factory=dict)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        raise NotImplementedError

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        raise NotImplementedError

    def set_availability(self, minutes: int, windows: List[Tuple[time, time]]) -> None:
        """Set total available minutes and the (start, end) time windows."""
        raise NotImplementedError

    def set_preference(self, key: str, value) -> None:
        """Store a scheduling preference."""
        raise NotImplementedError

    def get_all_tasks(self) -> List[Task]:
        """Return every task across all of the owner's pets."""
        raise NotImplementedError


@dataclass
class DailyPlan:
    date: date
    scheduled_tasks: List[Tuple[Task, time, str]] = field(default_factory=list)
    skipped_tasks: List[Tuple[Task, str]] = field(default_factory=list)
    total_minutes_used: int = 0

    def add_scheduled(self, task: Task, start: time, reason: str) -> None:
        """Record a task scheduled at a start time, with the reason it was chosen."""
        raise NotImplementedError

    def add_skipped(self, task: Task, reason: str) -> None:
        """Record a task that could not be scheduled, with the reason."""
        raise NotImplementedError

    def display(self) -> str:
        """Return the full plan formatted for display."""
        raise NotImplementedError

    def summary(self) -> str:
        """Return a short summary of the plan."""
        raise NotImplementedError


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner

    def generate_plan(self) -> DailyPlan:
        """Build a DailyPlan from the owner's tasks and availability."""
        raise NotImplementedError

    def sort_tasks(self) -> List[Task]:
        """Return the owner's tasks ordered by scheduling priority."""
        raise NotImplementedError

    def fits_in_time(self, task: Task, remaining_minutes: int) -> bool:
        """Return True if the task fits in the remaining minutes."""
        raise NotImplementedError

    def explain_choice(self, task: Task, reason: str) -> str:
        """Return a human-readable explanation of why a task was scheduled or skipped."""
        raise NotImplementedError
