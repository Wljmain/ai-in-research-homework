# Tools

Your AI agent runs these for you. Here they are if you'd rather work by hand. Run them from the repository root, on macOS, Linux or Windows. You need [uv](https://docs.astral.sh/uv/), git and the GitHub CLI; no Docker.

`uv run tools/hw.py` is the checklist your agent follows. It checks your setup and your task, and ends with one next step, saying who does it: the agent, you, or both of you together.

| Command | What it does |
|---|---|
| `uv run tools/hw.py` | The checklist and the next step |
| `uv run tools/hw.py plan` | What happens, start to finish |
| `uv run tools/hw.py new <task-name>` | Creates `week-1/submissions/<github-username>/<task-name>/` from `templates/`, on its own branch `week1-<task-name>` |
| `uv run tools/hw.py check [task-folder]` | The static checks CI runs, grouped by step |
| `uv run tools/hw.py approve instruction`, `window`, `publish` | You sign off at the three checkpoints. Only works in your own terminal |
| `uv run tools/hw.py note "<where we are, what's next>"` | Leaves a note for your next session |
| `uv run tools/hw.py submit --ai "<which AI helped, and how>"` | Commits, pushes and opens your pull request, or updates it |

`tools/hw.py` keeps a task's approvals in its `authoring/progress.json`, each with a fingerprint of the files it covered, so a later change shows up. What it knows about your computer (the GitHub login it saw) stays in `.git/hw.json` and never leaves your computer.

**Running tasks** happens on GitHub and on the instructor's machine, never on yours. `validate.sh` is what CI runs on every pull request: the static checks, then the reference solution must score 1 and a do-nothing agent 0, using Docker and [Harbor](https://github.com/harbor-framework/harbor). `check_task.py` holds the static checks; `ci_plan.py` and `reward.py` are helpers for CI.
