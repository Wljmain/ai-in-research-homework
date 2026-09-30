# Tools

Your AI agent runs these for you. Here they are if you'd rather work by hand. Run them from the repository root.

`tools/hw` is the checklist your agent follows. It checks your computer and your task, and ends with one next step, saying who does it: the agent, you, or both of you together.

| Command | What it does |
|---|---|
| `tools/hw` | The checklist and the next step |
| `tools/hw plan` | What happens, start to finish |
| `tools/hw new <task-name>` | Creates `week-1/submissions/<github-username>/<task-name>/` on its own branch, `week1-<task-name>` |
| `tools/hw check [task-folder]` | The static checks CI runs, grouped by step: fast, no Docker |
| `tools/hw validate` | The reference solution must score 1 and a do-nothing agent 0. Records the result |
| `tools/hw test-setup` | Runs the class example once, to prove Docker and Harbor work on your computer |
| `tools/hw approve instruction`, `window`, `publish` | You sign off at the three checkpoints. Only works in your own terminal |
| `tools/hw note "<where we are, what's next>"` | Leaves a note for your next session |
| `tools/hw submit --ai "<which AI helped, and how>"` | Commits, pushes and opens your pull request, or updates it |
| `uvx harbor@0.23.0 view jobs/validate` | Browses your validation runs in a web page |

`tools/hw` keeps a task's approvals and validation in its `authoring/progress.json`, each with a fingerprint of the files it covered, so a later change shows up. What it knows about your computer (the GitHub login it saw, the setup test) stays in `.git/hw.json` and never leaves your computer.

Underneath, `new_task.sh` scaffolds a task, `validate.sh` is exactly what CI runs, and `check_task.py` holds the static checks. `jobs/` holds every run's output and is never committed. `ci_plan.py` and `reward.py` are helpers used by CI and `validate.sh`.
