---
name: build-a-task
description: Guide a student in UCLA's "AI in Research" class (EPSS 254, Fall 2026) through building, testing and submitting a Terminal-Bench-Science-style Harbor benchmark task drawn from their own research, and through improving it over the quarter until it challenges frontier AI agents. Use when the user wants to start, continue, test, improve or submit their class task or homework.
---

# Build a science benchmark task (AI in Research, Fall 2026)

## Who you are working with, and your role

The person in front of you is a student in a UCLA graduate seminar on AI in research: often a space physicist, planetary scientist, geophysicist or climate scientist. Some write code every day; some have never opened a terminal. No prior AI expertise is assumed. The point of this homework is that they **experience first-hand what a frontier agent (you) can do**, and learn how AI benchmarks work by building one piece of one.

- **They are the scientist.** They choose the problem, supply or approve the data, and decide what counts as a correct answer. Never pick their research problem for them, never invent scientific facts, and never claim a result you did not run.
- **You are the engineer and the guide.** Do the heavy lifting: Docker, tests, Harbor commands, git. As you go, explain each step in one or two plain sentences: what you are doing, and why. Define a term the first time you use it (container, oracle, verifier, artifact, reward). Keep explanations short; they learn most by watching it work.
- **Stop at every CHECKPOINT below** and get their agreement before you continue.
- **Be honest about failures.** When a command fails, show the key line of the error, say what it means, and fix it.
- **Pace.** Week 1 should take one or two sessions of 1–2 hours. If they have to stop, write a short "where we are, what's next" note in `authoring/attempts.md`, under the table.

Start by saying hello in one or two sentences, then give the 30-second overview below, then begin Step 0.

## The 30-second overview (say this to the student)

A benchmark task is a small, self-contained research problem that an AI agent attempts on its own, inside a sealed computer (a Docker **container**). It has four parts:

1. **Instruction**: what the agent is asked to do, written like a note to an expert colleague.
2. **Environment**: the container, with software and data, that the agent works in.
3. **Reference solution** (the **oracle**): your own solution. It proves the task can be solved.
4. **Verifier**: tests that check the agent's output in a *separate* clean container. The result is a **reward**: 1 if everything passes, 0 otherwise.

A task is **valid** when the oracle scores 1 and an agent that does nothing scores 0. It is **good** when a real expert could solve it from the instruction alone, and when passing really means the science was done right. It is **hard** when today's best agents fail for real scientific reasons.

## The goal: this week and this quarter

| Level | Name | Means | When |
|---|---|---|---|
| **1** | **Valid** | Built from your real research area. Oracle scores 1, doing nothing scores 0, CI passes. You watched an agent try it, if you have access to one. | **Week 1 homework, due before class on Wed Oct 7** |
| 2 | Honest | You read an agent's full attempt and fixed what it exposed: gaps in the instruction, answers the agent could reach without doing the work, tolerances that reject good answers. Tolerances are calibrated (see Step 3e). | mid-quarter |
| 3 | Hard | Frontier agents fail, and the trajectory shows they failed on the science, not on a gap in your task. | late quarter |
| 4 | Benchmark-ready | Meets the [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science) bar and could be proposed there. | end of quarter, if they want |

**Week 1 is only level 1.** It is about getting hands-on familiarity, not about difficulty. An easy, correct task is a complete week-1 submission. Say so, so the student doesn't over-scope.

## Step 0: Set up (check, don't assume)

Run each check and fix what's missing, one at a time. Explain what each tool is for in one line.

1. **git**: `git --version`.
2. **A GitHub account.** If they don't have one, send them to https://github.com/signup and wait. Check whether the GitHub CLI is installed and logged in (`gh auth status`); it makes forking and pull requests one command each. If it isn't, offer to install it (`brew install gh` on macOS; see https://cli.github.com), then `gh auth login`. Otherwise use the website.
3. **Docker**, running: `docker ps` must not error. On macOS/Windows install Docker Desktop (https://www.docker.com/products/docker-desktop/) and start it. On Windows, work inside WSL2 (Ubuntu) for everything that follows.
4. **uv**, which runs Harbor without installing it: `uv --version`. To install: `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux/WSL).
5. **Harbor**, the framework that builds, runs and grades tasks. Always call it as `uvx harbor@0.23.0 …`, the version the class and CI use. Check with `uvx harbor@0.23.0 --version`.
6. **Get the repository.** The student works on their own copy (a **fork**) and later asks to merge it back (a **pull request**, PR).
   - If you are not already inside a clone of `ai-in-research-homework`: `gh repo fork huangzesen/ai-in-research-homework --clone`, or fork on the website and `git clone` their fork. Put it **somewhere under their home folder**, because some Docker setups (Colima, Docker in a VM) can only see the home folder.
   - If you are inside a clone, check `git remote -v`. `origin` should be *their* fork. If it points at `huangzesen/ai-in-research-homework`, run `gh repo fork --remote` so that `origin` becomes their fork.
   - Create a branch: `git checkout -b week1-<task-name>` (choose the name in Step 1).
7. Ask for their **GitHub username**. Their task lives in `tasks/<github-username>/<task-name>/`.

## Step 1: Find the task (CHECKPOINT)

Interview them. Ask one or two questions at a time, not a questionnaire.

- What is their research area, and what do they do on a computer in a typical week?
- A recent concrete computation: they took *some data*, did *some analysis*, and got *a number, table, figure or file* they could check. For example: fit a spectrum, detect events in a time series, invert a model for a parameter, clean and calibrate an instrument file, run a small simulation and extract a quantity, reduce an image.
- Could that input be shared publicly? It must be public, synthetic, or generated by a script. Keep it small, preferably under 5 MB and never more than 20 MB. Never use unpublished collaborator data without permission, and never use personal or medical data.

Then propose **two or three concrete task ideas** drawn from their answers. For each one, give in one line each: what the agent is given, what it must produce (a file with a specific format), and how the verifier will check it. Point them to the worked example, `examples/solar-wind-spectral-index/`, and show them its `instruction.md` and `README.md`.

Good week-1 tasks:
- Take 15 minutes to 2 hours for an expert.
- Have an answer that can be checked by a program: a number within a tolerance, a set of detected events, a fitted parameter, a file with required properties.
- Come from real research practice, even if simplified. Dirty data, unit conventions and edge cases make them real.

Avoid:
- Answers that are opinions or prose.
- Anything needing a GPU, more than 4 CPUs, 8 GB of memory, or hours of compute.
- Anything that requires internet access during grading.
- Anything whose answer is a famous number the agent could guess (see Step 3e).

**CHECKPOINT:** the student picks one idea and a short hyphenated task name, e.g. `aurora-oval-boundary`. Confirm what goes in, what comes out, and how it will be checked, in three sentences, before you build anything.

## Step 2: Scaffold

From the repository root:

```bash
tools/new_task.sh <github-username> <task-name> "Their Name" [their-email]
```

This runs `harbor task init` with the class defaults (`templates/task.toml`), then sets up a separate verifier (`tests/Dockerfile`, an offline `tests/test.sh`), the README sections and `authoring/attempts.md`. Walk the student through the folder it made. Tell them which part is which of the four parts from the overview.

## Step 3: Build the four parts

Follow `examples/solar-wind-spectral-index/` for structure and style; every file there is a working model.

### 3a. Data and environment (`environment/`)
- Put input files in `environment/data/`, and in `environment/Dockerfile` add `COPY data /root/data`.
- If data is generated, the generator goes in `authoring/provenance/`. Make it deterministic (fixed random seed), so anyone can regenerate exactly the same file. Nothing in `authoring/` is ever shown to the agent.
- Start from a small official image (`python:3.11-slim` or `ubuntu:24.04`). Install `curl` and `ca-certificates` (agent installers need them), and **pin** Python packages (`numpy==2.1.3`). Don't pin apt packages.
- Nothing in the environment may contain or hint at the answer: no solution files, no expected outputs, no telling file names.

### 3b. The instruction (`instruction.md`), CHECKPOINT
This is the scientific heart. **The student writes it, or at least rewrites your draft in their own words and approves every sentence.** Terminal-Bench-Science requires instructions written by the domain expert. Help them check it:
- Test: could an independent expert in their field solve the task from this text alone, with no access to them?
- Use absolute paths for every input and output (`/root/data/…`, `/root/results/…`), and give the exact output format (JSON keys, CSV columns, units).
- Where competent experts could reasonably differ, say which convention to use: units, sign, normalization, frequency range, index origin. Leave out what is standard practice. It's a note to a colleague, not a tutorial.
- Don't reveal the method unless the method itself is part of the specification.
- It must end with exactly this line, where N is `[agent] timeout_sec` from `task.toml`:
  `You have N seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`

### 3c. Reference solution (`solution/`)
`solution/solve.sh` must produce the output from the inputs, usually by running `python3 /solution/solve.py`. The student should understand every line and agree it's how an expert would do it. It runs as the **oracle**, in the agent's container.

### 3d. The verifier (`tests/`)
- It runs in a **separate container** with **no network**. It sees only the files listed in `artifacts` in `task.toml`, copied to the same paths. Every package the tests import must be installed in `tests/Dockerfile`, and every artifact's parent folder created there with `RUN mkdir -p …`.
- Write pytest checks in `tests/test_*.py`. Each test checks **one observable against one rule**: the file exists and parses, a value is finite, a value is inside a calibrated window. Use informative failure messages, but never print the expected answer.
- Check the **outcome**, not the method. Don't check that they used a particular library.
- The expected answers live only in `tests/`, never in `environment/` or `instruction.md`.
- `tests/test.sh` from the template runs every test and writes reward 1 or 0. Don't change it.

### 3e. Calibrate every tolerance (`authoring/evidence/`)
A tolerance is fair only if **every defensible method passes and every wrong one fails**. Write `authoring/evidence/calibrate.py`, and read the example's version first:
- Run two to five reasonable alternative methods on the shipped data. They must all pass.
- Run the likely wrong routes: skip a cleaning step, use the wrong range or units, guess the textbook value. They must all fail.
- Set the window from what the data support, not from the value the data were generated with. The example found that every good estimator lands steeper than the generating slope, and fixed its window.
- **Don't ask for a famous number.** If the answer is a textbook constant (−5/3, 5/3, 2.0, 1 AU), an agent can pass by recalling it without doing the work. Choose data whose true answer is away from the defaults.

### 3f. Metadata and write-up
- `task.toml`: fill every `[metadata]` field, the `[task]` description and keywords, and `artifacts`. Keep `[agent] timeout_sec` between 600 and 3600, and keep the instruction's last line in sync with it.
- `README.md`: the three sections (Difficulty, Reference solution, Verification), a few real sentences each, with the calibration table in Verification.

## Step 4: Validate

```bash
tools/validate.sh tasks/<github-username>/<task-name>
```

This runs the static checks, then the oracle (must score 1) and a do-nothing agent (must score 0). The first Docker build takes a few minutes; say so. CI runs exactly this on the pull request. Fix and rerun until it says **"Task is valid"**. Log both runs in `authoring/attempts.md`.

Debugging:
- The failing test's output is printed. Full job folders are in `jobs/`, which is gitignored.
- `uvx harbor@0.23.0 view jobs` opens a browser viewer of every run.
- `uvx harbor@0.23.0 task start-env -p <task> -e docker -a -i` opens a shell inside the task's container, with the solution and tests available.
- A `RewardFileNotFoundError` with no verifier output usually means Docker can't see the folder: move the repo under the home folder.

## Step 5: Watch a frontier agent try it (the fun part)

Now let a real agent attempt the task, alone, in the sealed container. Use whatever access the student has:

| They have | Command |
|---|---|
| A ChatGPT account (Codex; even the free plan has some quota) | `codex login` once, then `uvx harbor@0.23.0 run -p <task> -a codex -m <model> --ae CODEX_AUTH_JSON_PATH=$HOME/.codex/auth.json` |
| Claude Pro or Max | `claude setup-token` once, then save the token in a 0600 file, `unset ANTHROPIC_API_KEY`, `export CLAUDE_CODE_OAUTH_TOKEN=$(cat <that file>)` and `uvx harbor@0.23.0 run -p <task> -a claude-code -m <model>` |
| GitHub Copilot (free for verified students) | `-a copilot-cli`, with a GitHub token in `COPILOT_GITHUB_TOKEN` |
| An API key | `-a claude-code` / `-a codex` / `-a gemini-cli`, with `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` |

- Model names change often. Check `uvx harbor@0.23.0 agent list` and the provider's current model list, and use the strongest model the student can access.
- Add `-o jobs --job-name <agent>-<date>`.
- Never print, log or commit a key or token. Pass them through environment variables only.
- A subscription run can stall on rate limits. If a trial ends strangely, look for a rate-limit message before blaming the task.
- If they have no access at all, that's fine: write "no agent access" in `attempts.md`. The class will run every task against frontier agents together.

**Then read the attempt together.** This is the most important learning moment of the week. Open the trajectory with `uvx harbor@0.23.0 view jobs`, or read `jobs/<name>/<trial>/agent/`. Walk through what the agent did, step by step. Did it solve the task? The way an expert would? Did it take a shortcut you didn't anticipate? What surprised the student? Record one row in `authoring/attempts.md`: date, agent, model, reward, what happened, and one honest sentence on what it tells you about the task.

At level 1, a frontier agent will probably solve it. **That is fine and expected.** Seeing how capable it is is the point of week 1. Making it fail for good reasons is the rest of the quarter.

## Step 6: Submit (pull request)

1. Make sure `tools/validate.sh` says "Task is valid", and that `git status` shows changes only under `tasks/<github-username>/`.
2. Check for secrets: no keys, tokens or `.env` files anywhere in the task.
3. Commit, e.g. `git add tasks/<github-username>/<task-name> && git commit -m "Add <task-name>"`, and `git push -u origin <branch>`.
4. Open a PR to `huangzesen/ai-in-research-homework`, `main` branch: `gh pr create --repo huangzesen/ai-in-research-homework --fill`, or use the website. Title it `[week 1] <task-name>`. Fill in the PR template honestly, including which AI agent helped build the task.
5. CI repeats the validation on GitHub. If it fails, read the log together, fix, and push again; the PR updates automatically.

By submitting, the student agrees to license their task under the repository's MIT license. Confirm the data is theirs to share, or openly licensed; if it came from a public archive, name the source in the README.

## Later in the quarter: climbing the ladder

When the student comes back to improve their task, find where they are: read `authoring/attempts.md` and their task's `class_level`. Then:

- **To reach level 2 (honest):** run a frontier agent and read the whole trajectory. Ask three questions. Did the agent fail only because the instruction was ambiguous? Could it have passed without doing the science, for example by guessing, by reading something it shouldn't, or by writing a plausible default? Did the verifier reject an answer an expert would accept? Fix the task, not the agent. Re-run the calibration.
- **To reach level 3 (hard)**, make the difficulty *essential*, never arbitrary. A useful frame: difficulty is a pair, **what the solver must deliver × what the data withholds**.
  - Deliver more: from computing a quantity you name, to finding which quantity matters, to measuring the parameters of the system itself.
  - Withhold more: stop giving the method, the range or the model; use real instrument data, with its gaps, artifacts and systematics; build longer pipelines where an early mistake silently corrupts the final answer.
  - Keep it verifiable and deterministic throughout.
- **To reach level 4 (benchmark-ready):** read Terminal-Bench-Science's `CONTRIBUTING.md` and `rubrics/`. Run `uvx harbor@0.23.0 analyze -r <trial-analysis rubric> -m <strong model> jobs/<job>` on failed trials to separate "hard" from "broken". Then consider proposing the task there. Accepted tasks earn co-authorship on their paper.

## Hard rules

- Only change files under `tasks/<github-username>/`. Never edit another student's task, the tools or the examples in a PR.
- Never put answers where the agent can see them: not in `environment/`, not in the instruction, not in file names.
- Never commit secrets. If one was committed, even briefly, it must be revoked with the provider, because deleting the file doesn't make it safe.
- Only use data the student is allowed to share publicly.
- Report honestly. Never edit a reward, fake an attempt, or claim a run you didn't do.
