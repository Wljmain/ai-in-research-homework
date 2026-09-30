# AI in Research Homework

The hardest science tasks we can think of, built by the students, auditors and faculty of **AI in Research** (UCLA EPSS 254, Fall 2026). Each task is a real problem from our own fields, packaged in [Harbor](https://github.com/harbor-framework/harbor) format so that an AI agent can attempt it on its own, in a sealed container, and be graded automatically.

The question behind it: **what is the hardest thing in your field that a top expert can do, and that today's best AI agents can't?** Over the quarter we refine our tasks until they genuinely challenge frontier AI. That is a real achievement, and exactly what the people building these agents need.

## Week 1 homework: the hardest task in your field

**Due before class on Wednesday, October 7.** Think of the hardest task you can in your own research area, one with an answer a program can check, and package it in Harbor format. An AI coding agent does the engineering with you.

1. Open an AI coding agent (Claude Code, Codex, Cursor, GitHub Copilot, …) in a folder under your home directory.
2. Tell it:

   > Read https://class.xhelio.ai/week-1/homework.md and help me with my homework.

It walks you through everything: setting up, finding the hardest problem you can still verify, building and testing the task, letting a frontier agent attempt it, and opening your pull request.

**You'll need:** a [GitHub account](https://github.com/signup), [Docker](https://www.docker.com/products/docker-desktop/), [uv](https://docs.astral.sh/uv/) and an AI coding agent. The agent helps you install the rest. No AI subscription? Codex works with a free ChatGPT account, and GitHub Copilot is free for verified students.

## The levels

| Level | Name | Means | When |
|---|---|---|---|
| 1 | Ambitious | The hardest task you can think of in your field, in Harbor format. The reference solution scores 1, doing nothing scores 0, CI passes. A frontier agent tried it, if you have access. | Week 1 |
| 2 | Honest | You read agents' full attempts and fixed everything they exposed. Tolerances are calibrated: correct methods pass, wrong ones fail. | Mid-quarter |
| 3 | Proven hard | Frontier agents fail across several runs, on the science, not on a gap in your task. | Late quarter |
| 4 | Benchmark-ready | Meets the [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science) bar and could be proposed there. | End of quarter |

## What a task looks like

```
tasks/<github-username>/<task-name>/
├── instruction.md        what the agent is asked to do
├── task.toml             metadata, time limits, resources
├── environment/          the agent's container: Dockerfile + data
├── solution/             your reference solution (the "oracle"); may ship precomputed results
├── tests/                the verifier: its own container, no network, reward 1 or 0
├── README.md             difficulty, reference solution, verification
└── authoring/            how the data and reference were made, calibration, every agent attempt
```

The worked example, [`examples/solar-wind-spectral-index`](examples/solar-wind-spectral-index/), shows the **format**. It is deliberately easy. The last section of its [README](examples/solar-wind-spectral-index/README.md) shows how the same problem would become hard.

## Doing it by hand

```bash
tools/new_task.sh <github-username> <task-name> "Your Name"    # scaffold
tools/validate.sh tasks/<github-username>/<task-name>           # check, then oracle = 1 and nop = 0
uvx harbor@0.23.0 run -p tasks/<github-username>/<task-name> -a <agent> -m <model> -o jobs/runs   # let an agent try
```

Then open a pull request from your fork. CI runs `tools/validate.sh` on it.

## Rules

- Change only files under `tasks/<your-github-username>/`.
- Never commit API keys or tokens. Only use data you may share publicly.
- Be honest in `authoring/attempts.md` and in your PR, including which AI helped you.

## License and credits

[MIT](LICENSE). By opening a pull request you license your task under MIT.

Tasks use the [Harbor](https://github.com/harbor-framework/harbor) task format and follow the conventions of [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science). This repository is a class project, not affiliated with either.
