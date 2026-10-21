# Playbooks: reusable prompts

## 1. test-and-summarize (also a saved command: `/test-summary`)
> Run `scripts/check.sh`. Report PASS/FAIL and the first failing stage. For each failing test give name, one-line assertion and
> likely cause with a pointer into `main.py`. Do not edit files. Suggest the next command.

## 2. new endpoint (planner -> implementer -> reviewer)
1. *planner*: "Plan task N from docs/TASKS.md. Read AGENTS.md and intent.md first. Output files, API shape, schema + migration, failing tests first, risks."
2. Human reads the plan and approves or edits it.
3. *implementer*: "Implement this approved plan test-first. Show the failing test run before the fix. Run scripts/check.sh. Do not commit."
4. *reviewer*: "Review `git diff` against AGENTS.md, intent.md and the plan. Findings by severity and a verdict."
5. Human reviews the diff, then commits (the pre-commit hook re-runs the gate).

## 3. hook demonstration
Make a deliberately bad change (e.g. flip an assertion), `git commit`, and confirm the hook prints BLOCKED and exits 1.
