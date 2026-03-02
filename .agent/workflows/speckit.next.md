What speckit.next is responsible for
Purpose

Detect “where we are” in a Spec Kit project/feature.

Prompt the user with the most likely next step (single best action).

When the state is ambiguous, ask one targeted question or propose the safest default.

Keep the agent from jumping ahead to implementation before the required artifacts exist.

What it must NOT do

Not generate the artifacts itself “inline” unless the user explicitly chooses the next command.

Not skip required stages (e.g., don’t recommend /speckit.implement if tasks.md doesn’t exist).

Not re-litigate the whole methodology—just “what’s next”.

Canonical flow model (what “done” looks like)

Spec Kit’s README and methodology describe:

Core commands: /speckit.constitution, /speckit.specify, /speckit.plan, /speckit.tasks, /speckit.implement

Optional commands: /speckit.clarify (recommended before plan), /speckit.analyze (after tasks, before implement), /speckit.checklist

/speckit.tasks produces a tasks.md with ordering, dependencies, [P] parallel markers, checkpoints, and paths

/speckit.implement validates prerequisites and executes tasks from tasks.md

speckit.next decision rules

Think of speckit.next as a state detector + single recommendation.

Inputs it should consider

Which feature are we in?

Prefer the current feature directory (Spec Kit commonly uses feature directories; if feature detection is tricky, Spec Kit supports overriding feature detection with SPECIFY_FEATURE).

Artifact presence

.specify/memory/constitution.md

feature spec.md

feature plan.md (and any plan detail files your template creates)

feature tasks.md

Artifact freshness / drift (lightweight heuristics)

Has the user just changed requirements? If yes, steer back “upstream” (spec/plan/tasks).

Quality gates

If “underspecified”, suggest /speckit.clarify before /speckit.plan.

If tasks exist but consistency is uncertain, suggest /speckit.analyze before /speckit.implement.

Recommended “next step” mapping
1) No constitution yet → Next: /speckit.constitution

Trigger

.specify/memory/constitution.md missing (or clearly empty)

Prompt

“Next step is to lock project principles so every later decision is consistent. Run:
/speckit.constitution …”

2) Constitution exists, no spec yet → Next: /speckit.specify

Trigger

No feature spec.md

Prompt

“Next step is to define the ‘what and why’ (no tech stack). Run:
/speckit.specify …”

3) Spec exists but looks underspecified / user is unsure → Next: /speckit.clarify (recommended)

Trigger (examples)

Spec has vague language: “should”, “nice”, “somehow”, missing acceptance criteria, unclear data model, unclear non-functional requirements.

User asks questions that are requirements-shaped (“Should it do X?” “What about Y edge case?”)

Prompt

“Before we plan, we should close the biggest unknowns. Run:
/speckit.clarify”

4) Spec is stable, no plan yet → Next: /speckit.plan

Trigger

spec.md exists, but no plan.md

Prompt

“Next step is to choose the technical approach and architecture. Run:
/speckit.plan …”

5) Plan exists, no tasks yet → Next: /speckit.tasks

Trigger

plan.md exists, tasks.md missing

Prompt

“Next step is turning the plan into an executable task breakdown. Run:
/speckit.tasks”

6) Tasks exist, but we haven’t done a consistency pass → Next: /speckit.analyze (optional but valuable)

Trigger

tasks.md exists

Either (a) first run through, or (b) spec/plan changed after tasks were generated

Prompt

“Before implementing, do a cross-artifact consistency check. Run:
/speckit.analyze”

7) Prereqs satisfied → Next: /speckit.implement

Trigger

Constitution + spec + plan + tasks all exist

Optional analyze done (or user chooses to skip)

Prompt

“Ready to execute the task plan. Run:
/speckit.implement”

Drift handling (this is where speckit.next pays off)

When the user changes something, speckit.next should route them back upstream:

User changed requirements (spec drift)

Recommend: update spec.md first (or rerun /speckit.specify if that’s their practice), then rerun /speckit.plan, then /speckit.tasks.

Rationale: tasks are derived from plan, plan is derived from spec.

User changed architecture/tooling (plan drift)

Recommend: update plan.md, then rerun /speckit.tasks, then optionally /speckit.analyze.

Tasks edited manually / partial completion

Recommend: either:

proceed with /speckit.implement if tasks still coherent, or

/speckit.analyze if unsure.

Output contract for speckit.next

Keep it consistent and short. Suggested structure:

Detected stage

“We have: constitution ✅, spec ✅, plan ❌, tasks ❌ …”

Recommendation (one action)

“Next: /speckit.plan”

Why (one sentence)

“We can’t generate tasks until the implementation plan exists.”

If user is uncertain

Offer exactly one “fork”:

“If you’re still deciding X, run /speckit.clarify first.”