import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))


def flash_and_rerun(message: str) -> None:
    """Show a toast on the next run, so it appears after the page refreshes."""
    st.session_state.flash = message
    st.rerun()


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
        if st.form_submit_button("Add task"):
            pet = owner.pets[pet_choice]
            title = task_title.strip() or "Untitled task"
            if any(t.title.lower() == title.lower() for t in pet.tasks):
                st.error(f"{pet.name} already has a task called '{title}'.")
            else:
                pet.add_task(
                    Task(
                        title=title,
                        category=category,
                        duration_minutes=int(duration),
                        priority=priority,
                        frequency=frequency,
                        preferred_time=preferred if use_time else None,
                    )
                )
                flash_and_rerun(f"Added '{title}' for {pet.name}.")

    # Finished tasks (already replaced by their next occurrence) are hidden from the list
    all_tasks = [t for t in Scheduler(owner).sort_by_time() if t.next_occurrence is None]
    if all_tasks:
        st.write("Current tasks:")
        st.dataframe(
            [
                {
                    "Pet": t.pet.name,
                    "Task": t.title,
                    "Category": t.category,
                    "Minutes": t.duration_minutes,
                    "Priority": t.priority,
                    "Frequency": t.frequency,
                    "Preferred time": t.preferred_time.strftime("%H:%M") if t.preferred_time else "",
                    "Status": "Due today" if t.is_due_today() else f"Due {t.due_date.isoformat()}",
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
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

tasks_due = [t for t in owner.get_all_tasks() if t.is_due_today()]
if not owner.get_all_tasks():
    st.info("Add at least one task to see today's schedule.")
else:
    needed = sum(t.duration_minutes for t in tasks_due)
    if needed > owner.available_minutes:
        st.warning(
            f"Tasks due today total {needed} min but you have {owner.available_minutes} min. "
            "Lowest-priority tasks will be skipped."
        )
    plan = Scheduler(owner).generate_plan()
    for warning in plan.warnings:
        st.warning(f"{warning}. One of them will be moved to the next free slot or skipped.")
    st.success(plan.summary())
    st.text(plan.display())
