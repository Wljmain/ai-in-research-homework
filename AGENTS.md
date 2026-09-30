# AGENTS.md

This repository collects science benchmark tasks built by students in UCLA's **AI in Research** class (EPSS 254, Fall 2026), in the [Harbor](https://github.com/harbor-framework/harbor) task format, following [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science) conventions.

**If the user wants to create, continue, test, improve or submit their class task (the week 1 homework or later), read `.agents/skills/build-a-task/SKILL.md` now and follow it from the top.** It explains your role: you guide the student and do the engineering; they are the scientist.

Map:
- `tasks/<github-username>/<task-name>/`: student tasks, one folder per student
- `examples/`: worked examples; start with `solar-wind-spectral-index/`
- `templates/`: class defaults used by `tools/new_task.sh`
- `tools/new_task.sh`: scaffold a task
- `tools/validate.sh`: static checks, then oracle must score 1 and nop must score 0 (CI runs the same)
- `tools/check_task.py`: the static checks alone

Rules: only edit files under `tasks/<github-username>/`; never commit secrets; always run Harbor as `uvx harbor@0.23.0`.
