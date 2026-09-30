# AGENTS.md

This is the homework repository of UCLA's **AI in Research** class (EPSS 254, Fall 2026). Each week's assignment is in `week-<n>/README.md`. Submissions go in `week-<n>/submissions/<github-username>/`, by pull request from the student's fork.

**Week 1, and any later work on a benchmark task:** read `.agents/skills/build-a-task/SKILL.md` now and follow it from the top. It explains your role: you guide the student and do the engineering; they are the scientist.

Map:
- `week-<n>/`: the assignment (`README.md`), an example, and `submissions/`
- `templates/`, `tools/`: shared scaffolding and checks (see `tools/README.md`); CI runs `tools/validate.sh` on every benchmark task

Rules: only edit files under `week-<n>/submissions/<github-username>/`; never commit secrets; always run Harbor as `uvx harbor@0.23.0`.
