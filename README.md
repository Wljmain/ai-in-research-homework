# AI in Research Homework

Science benchmark tasks built by the students of **AI in Research** (UCLA EPSS 254, Fall 2026). Each task is a real problem from our own research, packaged so that an AI agent can attempt it on its own in a sealed container and be graded automatically.

Over the quarter, each of us builds one task and improves it until it **challenges the best AI agents available**. That is hard, and it is exactly what the people building these agents need.

## Week 1 homework: build your first task

**Due before class on Wednesday, October 7.** You'll build it together with an AI coding agent, which is half the point: see first-hand what a frontier agent can do.

1. Open an AI coding agent (Claude Code, Codex, Cursor, GitHub Copilot, …) in a folder under your home directory.
2. Tell it:

   > Read https://class.xhelio.ai/week-1/homework.md and help me with my homework.

It will walk you through everything: setting up, choosing a problem from your research, building and testing the task, watching a frontier agent attempt it, and opening your pull request.

**You'll need:** a [GitHub account](https://github.com/signup), [Docker](https://www.docker.com/products/docker-desktop/), [uv](https://docs.astral.sh/uv/) and an AI coding agent. The agent helps you install the rest. No AI subscription? Codex works with a free ChatGPT account, and GitHub Copilot is free for verified students.

Week 1 is about getting hands-on, not about difficulty: **an easy, correct task is a complete submission.**

## The levels

| Level | Name | Means | When |
|---|---|---|---|
| 1 | Valid | Built from your research area. The reference solution scores 1, doing nothing scores 0, CI passes. You watched an agent try it. | Week 1 |
| 2 | Honest | You read an agent's full attempt and fixed what it exposed. Tolerances are calibrated: correct methods pass, wrong ones fail. | Mid-quarter |
| 3 | Hard | Frontier agents fail, and they fail on the science, not on a gap in your task. | Late quarter |
| 4 | Benchmark-ready | Meets the [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science) bar and could be proposed there. | End of quarter |

## What a task looks like

```
tasks/<github-username>/<task-name>/
├── instruction.md        what the agent is asked to do
├── task.toml             metadata, time limits, resources
├── environment/          the agent's container: Dockerfile + data
├── solution/             your reference solution (the "oracle")
├── tests/                the verifier: its own container, no network, reward 1 or 0
├── README.md             difficulty, reference solution, verification
└── authoring/            how the data was made, tolerance calibration, every agent attempt
```

The worked example is [`examples/solar-wind-spectral-index`](examples/solar-wind-spectral-index/). Read its [README](examples/solar-wind-spectral-index/README.md).

## Doing it by hand

```bash
tools/new_task.sh <github-username> <task-name> "Your Name"    # scaffold
tools/validate.sh tasks/<github-username>/<task-name>           # check, then oracle = 1 and nop = 0
uvx harbor@0.23.0 run -p tasks/<github-username>/<task-name> -a <agent> -m <model>   # let an agent try
```

Then open a pull request from your fork. CI runs `tools/validate.sh` on it.

## Rules

- Change only files under `tasks/<your-github-username>/`.
- Never commit API keys or tokens. Only use data you may share publicly.
- Be honest in `authoring/attempts.md` and in your PR, including which AI helped you.

## License and credits

[MIT](LICENSE). By opening a pull request you license your task under MIT.

Tasks use the [Harbor](https://github.com/harbor-framework/harbor) task format and follow the conventions of [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science). This repository is a class project, not affiliated with either.
