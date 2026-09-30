# Week 1: the hardest task in your field

**Due before class on Wednesday, October 7, 2026.**

What is the hardest thing in your field that a top expert can do on a computer, with an answer that can be checked, and that today's best AI agents can't? Design that task, and package it as a benchmark task: a problem an AI agent attempts on its own, in a sealed container, graded automatically. Then watch a frontier agent try.

Aim high. An AI coding agent does the engineering with you; you bring the science.

## Start

1. Open an AI coding agent (Claude Code, Codex, Cursor, GitHub Copilot, …) in a folder under your home directory.
2. Give it this:

   > Read https://class.xhelio.ai/week-1/homework.md and help me with my homework.

It walks you through setup, finding the hardest problem you can still verify, building and testing the task, letting a frontier agent attempt it, and opening your pull request.

**You'll need:** a [GitHub account](https://github.com/signup), [Docker](https://www.docker.com/products/docker-desktop/), [uv](https://docs.astral.sh/uv/) and an AI coding agent. Your agent helps you install the rest. No AI subscription? Codex works with a free ChatGPT account, and GitHub Copilot is free for verified students.

## What you submit

A folder `week-1/submissions/<your-github-username>/<task-name>/` in [Harbor](https://github.com/harbor-framework/harbor) format:

```
instruction.md        what the agent is asked to do
task.toml             metadata, time limits, resources
environment/          the agent's container: Dockerfile + data
solution/             your reference solution; may ship precomputed results
tests/                the verifier: its own container, no network, reward 1 or 0
README.md             difficulty, reference solution, verification
authoring/            how the data and reference were made, every agent attempt
```

It counts when your reference solution scores 1, an agent that does nothing scores 0, and the automatic checks pass. The [format example](example/solar-wind-spectral-index/) shows every file. It is deliberately easy; its README ends with how that same problem would become hard.

## Over the quarter

We'll keep refining these tasks until they genuinely challenge frontier AI:

1. **Ambitious:** the hardest task you can think of, valid in Harbor format (this week)
2. **Honest:** you read agents' full attempts and fixed everything they exposed
3. **Proven hard:** frontier agents fail, repeatedly, on the science itself
4. **Benchmark-ready:** good enough to propose to [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science)
