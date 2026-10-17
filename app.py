from datetime import date, time

import streamlit as st

from pawpal_system import DependencyCycleError, MustDoError, Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))


def flash_and_rerun(message: str) -> None:
    """Show a toast on the next run, so it appears after the page refreshes."""
    st.session_state.flash = message
    st.rerun()


PRIORITY_ICONS = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def task_status(task: Task) -> str:
    """Short status label for the task table."""
    if task.is_due_today():
        return "⏰ Due today"
    if task.due_date is not None and task.due_date > date.today():
        return f"📅 Due {task.due_date.isoformat()}"
    return "✅ Done"


st.title("🐾 PawPal+")

st.markdown("Plan your pets' daily care and see why each task was scheduled or skipped.")

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

# The Owner lives in session_state so it survives Streamlit's reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=120)
owner = st.session_state.owner
scheduler = Scheduler(owner)

st.divider()

st.subheader("Owner")
col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    minutes = st.number_input(
        "Minutes available today", min_value=0, max_value=1440, value=owner.available_minutes
    )
owner.set_availability(int(minutes), owner.time_windows)

st.divider()

st.subheader("Add a Pet")
with st.form("add_pet_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name")
        species = st.selectbox("Species", ["dog", "cat", "other"])
        age = st.number_input("Age", min_value=0, max_value=40, value=1)
    with col2:
        breed = st.text_input("Breed")
        special_needs = st.text_input("Special needs", placeholder="e.g. thyroid medication")
    if st.form_submit_button("Add pet"):
        name = pet_name.strip()
        if not name:
            st.error("Please enter a pet name.")
        elif any(p.name.lower() == name.lower() for p in owner.pets):
            st.error(f"You already have a pet named {name}.")
        else:
            owner.add_pet(
                Pet(
                    name=name,
                    species=species,
                    breed=breed.strip(),
                    age=int(age),
                    special_needs=special_needs.strip(),
                )
            )
            flash_and_rerun(f"Added {name}.")

if owner.pets:
    st.dataframe(
        [
            {
                "Name": p.name,
                "Species": p.species,
                "Breed": p.breed,
                "Age": p.age,
                "Special needs": p.special_needs,
                "Tasks": len(p.tasks),
            }
            for p in owner.pets
        ],
        hide_index=True,
        width="stretch",
    )
    remove_col1, remove_col2 = st.columns([3, 1], vertical_alignment="bottom")
    with remove_col1:
        pet_to_remove = st.selectbox(
            "Remove a pet", range(len(owner.pets)), format_func=lambda i: owner.pets[i].name
        )
    with remove_col2:
        if st.button("Remove pet"):
            removed = owner.pets[pet_to_remove]
            owner.remove_pet(removed)
            flash_and_rerun(f"Removed {removed.name} and their tasks.")
else:
    st.info("No pets yet. Add one above.")

st.divider()

st.subheader("Add a Task")
if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    # Outside the form so the time picker can react to it right away.
    use_time = st.checkbox("Set a preferred time", key="task_use_time")
    # Widget keys keep the last-used values between additions.
    with st.form("add_task_form"):
        pet_choice = st.selectbox("Pet", range(len(owner.pets)), format_func=lambda i: owner.pets[i].name)
        task_title = st.text_input("Task title", value="Morning walk", key="task_title")
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox(
                "Category", ["walk", "feeding", "meds", "enrichment", "grooming"], key="task_category"
            )
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20, key="task_duration"
            )
        with col2:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2, key="task_priority")
            frequency = st.selectbox("Frequency", ["daily", "weekly"], key="task_frequency")
        with col3:
            preferred = st.time_input("Preferred time", disabled=not use_time, key="task_preferred")
        # Used by the optimal planner. Dependencies are titles of the chosen pet's tasks.
        depends_on = st.multiselect(
            "Must come after (optional)",
            sorted({t.title for t in owner.get_all_tasks()}),
            key="task_depends",
        )
        min_gap = st.number_input(
            "Minimum gap from other tasks of this category (minutes, 0 = none)",
            min_value=0,
            max_value=1440,
            value=0,
            key="task_gap",
        )
        if st.form_submit_button("Add task"):
            pet = owner.pets[pet_choice]
            title = task_title.strip() or "Untitled task"
            if any(t.title.lower() == title.lower() for t in pet.tasks):
                st.error(f"{pet.name} already has a task called '{title}'.")
            elif any(d not in {t.title for t in pet.tasks} or d.lower() == title.lower() for d in depends_on):
                st.error(f"'Must come after' can only list other tasks that {pet.name} has.")
            else:
                new_task = Task(
                    title=title,
                    category=category,
                    duration_minutes=int(duration),
                    priority=priority,
                    frequency=frequency,
                    preferred_time=preferred if use_time else None,
                    depends_on=list(depends_on),
                    min_gap_minutes=int(min_gap) or None,
                )
                pet.add_task(new_task)
                try:
                    scheduler.order_by_dependencies()
                except DependencyCycleError as error:
                    pet.remove_task(new_task)
                    st.error(f"Task not added. {error}")
                else:
                    flash_and_rerun(f"Added '{title}' for {pet.name}.")

    # Filter with Scheduler.filter_tasks, then order by preferred time with Scheduler.sort_by_time.
    # "Pending" hides finished tasks (already replaced by their next occurrence).
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        pet_filter = st.selectbox("Show pet", ["All pets"] + [p.name for p in owner.pets])
    with filter_col2:
        status_filter = st.selectbox("Show status", ["Pending", "Completed", "All"])
    with filter_col3:
        sort_choice = st.selectbox("Sort by", ["Priority, then time", "Time"])
    sorter = scheduler.sort_by_priority if sort_choice == "Priority, then time" else scheduler.sort_by_time
    all_tasks = sorter(
        scheduler.filter_tasks(
            completed={"Pending": False, "Completed": True, "All": None}[status_filter],
            pet_name=None if pet_filter == "All pets" else pet_filter,
        )
    )
    if all_tasks:
        st.success(f"Showing {len(all_tasks)} task(s), sorted by {sort_choice.lower()}.")
        st.dataframe(
            [
                {
                    "Pet": t.pet.name,
                    "Task": t.title,
                    "Category": t.category,
                    "Minutes": t.duration_minutes,
                    "Priority": f"{PRIORITY_ICONS[t.priority]} {t.priority.capitalize()}",
                    "Frequency": t.frequency.capitalize(),
                    "Preferred time": t.preferred_time.strftime("%H:%M") if t.preferred_time else "—",
                    "After": ", ".join(t.depends_on) or "—",
                    "Min gap": f"{t.min_gap_minutes} min" if t.min_gap_minutes else "—",
                    "Status": task_status(t),
                }
                for t in all_tasks
            ],
            hide_index=True,
            width="stretch",
        )

        due_tasks = [t for t in all_tasks if t.is_due_today()]
        if due_tasks:
            done_col1, done_col2 = st.columns([3, 1], vertical_alignment="bottom")
            with done_col1:
                task_to_complete = st.selectbox(
                    "Mark a task complete",
                    range(len(due_tasks)),
                    format_func=lambda i: f"{due_tasks[i].pet.name}: {due_tasks[i].title}",
                )
            with done_col2:
                if st.button("Mark complete"):
                    task = due_tasks[task_to_complete]
                    next_task = task.mark_complete()
                    flash_and_rerun(f"Completed '{task.title}'. Next one is due {next_task.due_date.isoformat()}.")

        remove_col1, remove_col2 = st.columns([3, 1], vertical_alignment="bottom")
        with remove_col1:
            task_to_remove = st.selectbox(
                "Remove a task",
                range(len(all_tasks)),
                format_func=lambda i: f"{all_tasks[i].pet.name}: {all_tasks[i].title}",
            )
        with remove_col2:
            if st.button("Remove task"):
                task = all_tasks[task_to_remove]
                task.pet.remove_task(task)
                flash_and_rerun(f"Removed '{task.title}'.")
    elif owner.get_all_tasks():
        st.info("No tasks match these filters.")
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

if not owner.get_all_tasks():
    st.info("Add at least one task to see today's schedule.")
else:
    needed = sum(t.duration_minutes for t in scheduler.filter_tasks(completed=False) if t.is_due_today())
    if needed > owner.available_minutes:
        st.warning(
            f"Tasks due today total {needed} min but you have {owner.available_minutes} min. "
            "Lowest-priority tasks will be skipped."
        )
    planner = st.radio(
        "Planner",
        ["Greedy (fast)", "Optimal (best score)"],
        horizontal=True,
        help="Greedy places tasks in priority order. Optimal searches for the highest-scoring plan "
        "that respects windows, dependencies, minimum gaps and must-do meds.",
    )
    greedy_plan = scheduler.generate_plan()
    plan = greedy_plan
    if planner.startswith("Optimal"):
        try:
            plan = scheduler.optimal_plan()
        except (MustDoError, DependencyCycleError) as error:
            st.error(str(error))
            st.stop()
        st.caption(
            f"Plan score: {scheduler.plan_score(plan)} points "
            f"(the greedy plan scores {scheduler.plan_score(greedy_plan)})."
        )
    # Tasks that are simply not due yet are noise; only report real skips
    real_skips = [t for t, _reason in plan.skipped_tasks if t.is_due_today()]
    for warning in plan.warnings:
        if planner.startswith("Optimal"):
            st.warning(warning)
        else:
            st.warning(f"{warning}. One of them will be moved to the next free slot or skipped.")
    # Headline numbers, then a clear success/warning for the overall result
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Scheduled", len(plan.scheduled_tasks))
    metric2.metric("Skipped", len(real_skips))
    metric3.metric("Minutes used", f"{plan.total_minutes_used} / {owner.available_minutes}")
    if real_skips:
        st.warning(plan.summary())
    else:
        st.success(plan.summary())

    if plan.scheduled_tasks:
        st.markdown("#### Today's schedule")
        st.table(
            [
                {
                    "Time": start.strftime("%H:%M"),
                    "Pet": t.pet.name if t.pet else "Unassigned",
                    "Task": t.title,
                    "Minutes": t.duration_minutes,
                    "Priority": f"{PRIORITY_ICONS[t.priority]} {t.priority.capitalize()}",
                    "Why": reason,
                }
                for t, start, reason in sorted(plan.scheduled_tasks, key=lambda e: e[1])
            ]
        )
    else:
        st.info("Nothing is scheduled for today.")

    st.markdown("#### Find a free slot")
    slot_col1, slot_col2, slot_col3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    with slot_col1:
        slot_minutes = st.number_input("Task length (minutes)", min_value=1, max_value=240, value=30, key="slot_minutes")
    with slot_col2:
        slot_after = st.time_input("Not before", value=time(8, 0), key="slot_after")
    with slot_col3:
        find_slot = st.button("Find slot")
    if find_slot:
        slot = scheduler.find_next_available_slot(int(slot_minutes), earliest=slot_after)
        if slot is None:
            st.warning(f"No free {int(slot_minutes)}-minute slot left today.")
        else:
            st.success(f"Next free {int(slot_minutes)}-minute slot starts at {slot.strftime('%H:%M')}.")

    if real_skips:
        st.markdown("#### Skipped")
        for t in real_skips:
            st.warning(scheduler.explain_choice(t))
