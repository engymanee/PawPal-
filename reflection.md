# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
  1. **Add a pet profile.** Enter the pet’s name, species or breed, age and any special needs, such as medication or a diet.
  2. **Add, edit or remove care tasks.** Create a task like “Morning walk” with a duration, a priority (high, medium or low), a frequency (daily or weekly) and an optional preferred time.
  3. **Set daily constraints and preferences.** Tell the app how much time is available today, which time windows work (for example, “free 7–8am and 6–9pm”), and preferences such as “walks before work” or “no grooming on weekdays”.
  4. **Generate a daily plan.** The app schedules tasks into the available time, puts high-priority ones like meds and feeding first, and skips or postpones whatever doesn’t fit.
  5. **See why the plan looks the way it does, then mark tasks done.** Each scheduled or skipped task comes with a reason, like “Meds scheduled first: high priority, fixed time” or “Grooming skipped: not enough time today”. The owner can then check tasks off as they complete them.

- What classes did you include, and what responsibilities did you assign to each?

  1. **Task** represents one pet care activity, such as a walk, a feeding or a dose of medication. It stores the title, category, duration, priority, frequency and an optional preferred time. It can mark itself complete, report whether it’s due today, and turn its priority into a number for sorting.
  2. **Pet** stores a pet’s basic profile (name, species, breed, age and any special needs) and owns that pet’s list of tasks. It handles adding, editing, removing and returning those tasks.
  3. **Owner** represents the person using the app. It holds their pets, the minutes they have available each day, their available time windows and their scheduling preferences. It can also collect every task across all of their pets, so the scheduler has one place to get them from.
  4. **Scheduler** is the decision-making part of the system. It takes an Owner, sorts the tasks by priority and preferred time, checks whether each one fits in the remaining time, and records why it scheduled or skipped each task. Its main method, `generate_plan()`, returns a DailyPlan.
  5. **DailyPlan** holds the result: the date, the scheduled tasks with their start times and reasons, the skipped tasks with their reasons, and the total minutes used. It can display the full plan or give a short summary.

**b. Design changes**

- Did your design change during implementation?
Yes, I did

- If yes, describe at least one change and why you made it.
1. Before, category, priority and frequency were plain str fields, so any text was accepted. I changed them to Literal types, which list the exact values each field is allowed to have. After implementing that I noticed that Literal was never imported so I imported it.
2. I added a `pet` field to Task so each task knows which pet it belongs to.
3. I added an `owner` field to Pet so each pet knows who owns it.
4. I created a new TimeWindow class, and Owner now uses it instead of plain (start, end) pairs.
5. I added an `owner` field to DailyPlan so a plan knows who it is for.
6. I renamed DailyPlan's `date` field to `plan_date` because it clashed with the `date` type.
7. I added `get_reason(task)` to DailyPlan to look up why a task was scheduled or skipped.
8. I added `complete_task(task)` to DailyPlan so finishing a task is connected to the plan.
9. I gave Scheduler a `plan` attribute that remembers the latest plan it generated.
10. I changed `explain_choice` to take only `task` and read the reason from the saved plan.
11. I added `from __future__ import annotations` so classes can refer to ones defined later in the file.
12. I updated the UML diagram to match all of these changes.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
  My scheduler is greedy. `generate_plan()` sorts the tasks once (highest priority first, then earliest preferred time, then shortest) and places them in that order. Each task goes at its preferred time if it fits, or in the earliest free slot if not, and a task that doesn't fit is skipped. It never goes back to rearrange earlier choices. This means it can be less than optimal. For example, a long high-priority task can use up minutes that would have fit several shorter tasks, and two tasks that ask for the same time are not negotiated: one is moved, and I only report the overlap as a warning from `find_conflicts()`.

- Why is that tradeoff reasonable for this scenario?
  A pet owner has a short list of tasks, and the most important ones, like medication and feeding, must happen even if the day is full. Putting high priority first guarantees that, which matters more than packing in as many tasks as possible. A greedy pass is also easy to explain, and the app's main promise is showing why each task was scheduled or skipped. Because the rules are simple, every reason can be one clear sentence, such as "High priority" or "preferred time not available so used the earliest free slot". A smarter search could fit more tasks in, but it would be harder to understand and to test, and for a handful of tasks the extra complexity isn't worth it.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
  I used Claude Code throughout the project. I used it for design brainstorming, to turn my UML diagram into a Python class skeleton, and to fill in the method logic step by step. I also used it to review the design as I went, which is how I caught missing pieces like the `Literal` import and the back-references between Task, Pet and Owner. Near the end I used it for the small cleanup jobs: adding one-line docstrings and writing the README implementation summary.

- What kinds of prompts or questions were most helpful?
  The most helpful prompts were small and specific, such as "add 1-line docstrings to the methods in pawpal_system.py" or "write a short summary of how the classes work together". They gave me a result I could check quickly. Prompts that pointed the AI at my existing UML and files worked better than open-ended ones, because the answers matched my design instead of inventing a new one. Asking it to explain why a design choice was made was also useful, because I learned something and could decide whether I agreed.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
  When the AI turned my UML into a class skeleton, I did not accept it as written. The skeleton used a `date` field on DailyPlan, which clashed with the `date` type imported from `datetime`, so I renamed it to `plan_date`. I also noticed that the `Literal` types for category, priority and frequency were used but never imported, so I added the import myself.

- How did you evaluate or verify what the AI suggested?
  I read the generated code against my UML diagram and checked each field and method one by one. I ran the code to catch errors like the missing import, and I updated the UML to match what the code actually does. I also wrote tests in `tests/` for the main scheduling behaviors instead of trusting that the logic worked.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
