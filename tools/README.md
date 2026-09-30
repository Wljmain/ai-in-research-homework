# Tools

Your AI agent runs these for you. Here they are if you'd rather work by hand. Run them from the repository root. You need Docker and [uv](https://docs.astral.sh/uv/); Harbor runs through `uvx`, so it doesn't need installing.

| Command | What it does |
|---|---|
| `tools/new_task.sh <github-username> <task-name> "Your Name"` | Scaffolds `week-1/submissions/<github-username>/<task-name>/` (set `WEEK=week-N` for another week) |
| `tools/validate.sh <task-folder>` | Static checks, then the reference solution must score 1 and a do-nothing agent 0. CI runs exactly this. |
| `uv run --python 3.12 tools/check_task.py <task-folder>` | The static checks alone: fast, no Docker |
| `uvx harbor@0.23.0 run -p <task-folder> -a <agent> -m <model> -o jobs/runs` | Lets a real agent attempt the task |
| `uvx harbor@0.23.0 view jobs/runs` | Browses runs and agent trajectories in a web page |

`jobs/` holds every run's output and is never committed. `ci_plan.py` and `reward.py` are helpers used by CI and `validate.sh`.
