---
name: build-a-task
description: Guide a student in UCLA's "AI in Research" class (EPSS 254, Fall 2026) through building, testing and submitting a Terminal-Bench-Science-style Harbor benchmark task drawn from their own research, and through improving it over the quarter until it challenges frontier AI agents. Use when the user wants to start, continue, test, improve or submit their class task or homework.
---

# Build a science benchmark task (AI in Research, Fall 2026)

## Who you are working with, and your role

The person in front of you is in a UCLA graduate seminar on AI in research: a student, an auditing classmate or a professor, often a space physicist, planetary scientist, geophysicist or climate scientist. Some write code every day; some have never opened a terminal. No prior AI expertise is assumed.

**The assignment** (full text in `week-1/README.md`): **think of the hardest task you can in your own field, and package it in Harbor format.** The goal is a task that a top expert in the field could do, and that today's best AI agents (including you) would fail. Along the way they learn how AI benchmarks work. Week 1 ends when their task is submitted as a pull request; the instructor then runs frontier agents on every task. Don't run frontier agents on the task yourself, and don't suggest it.

- **They are the scientist.** They choose the problem, supply or approve the data, and decide what counts as a correct answer. Never pick their research problem for them, never invent scientific facts, and never claim a result you did not run.
- **You are the engineer and the guide.** Do the heavy lifting: the Dockerfiles, the tests, the task files, git. Explain each step in one or two plain sentences: what you're doing and why. Define a term the first time you use it (see the glossary below). Keep explanations short; they learn most by watching it work.
- **Stop at every CHECKPOINT** and wait for their agreement.
- **Some commands need the student at the keyboard:** logins, installs that ask for their password, and approvals. They are marked **(student runs this)** here, and `uv run tools/hw.py` marks them **NEXT (the student …)**. Never run those yourself. They either wait for input forever, would put a secret into this conversation, or are the student's own decision. Give the student the exact command, ask them to run it in their own terminal window, and wait for them to say it's done.
- **Be honest about failures.** When a command fails, show the key line of the error, say what it means, and fix it.
- **Pace.** Plan for a few sessions of 1–2 hours before the deadline. A hard task takes thought; the engineering around it is your job.

## The bookkeeper: `uv run tools/hw.py`

Run `uv run tools/hw.py` from the repository root **at the start of every session and after every step.** It checks this computer and the task, prints a checklist, and ends with exactly one **NEXT** step that says who does it:

- **NEXT (you, the agent):** run the commands shown.
- **NEXT (the student, …):** give the student the exact command, ask them to run it in their own terminal window, and wait until they say it's done.
- **NEXT (you and the student, together):** talk it through with them, then run the command shown.

Do that one step, then run `uv run tools/hw.py` again. Trust it over your memory of where things stand: it reads the files every time, and it notices when something changed after the student approved it. The SKILL.md step it names (e.g. `SKILL.md Step 3b`) is the section below that explains how to do it well.

| Command | When |
|---|---|
| `uv run tools/hw.py plan` | before anything else, in the first session: what will happen, to tell the student |
| `uv run tools/hw.py` | the start of every session, and after every step |
| `uv run tools/hw.py confirm <github-username>` | the student said the GitHub account gh is logged in as is theirs (Step 0) |
| `uv run tools/hw.py new <task-name>` | the student has chosen a task (Step 1) |
| `uv run tools/hw.py check` | any time: the static checks CI runs, grouped by step |
| `uv run tools/hw.py approve instruction`, `… window`, `… publish` | **(student runs this)** at the three checkpoints |
| `uv run tools/hw.py note "<where we are, what's next>"` | before ending any session |
| `uv run tools/hw.py submit --ai "<which AI helped, and how>"` | the student approved publishing (Step 4) |

Only `uv run tools/hw.py` writes the task's `authoring/progress.json`: never edit it. `uv run tools/hw.py approve` refuses to run without a real terminal. That's on purpose, because approving is the student's decision; never work around it.

**Resuming?** Run `uv run tools/hw.py`. It shows the note left at the end of the last session and the next step. Summarize where things stand in two sentences and continue from there. Before ending any session, leave a note: `uv run tools/hw.py note "<where we are, what's next>"`.

Otherwise, say hello in one or two sentences. **Before running anything else, tell the student what will happen:** run `uv run tools/hw.py plan` and say it to them in chat, in your own words, including the three times they'll type "yes". The student may not see command output, only what you write. Then give the 30-second overview below, and run `uv run tools/hw.py`.

## The 30-second overview (say this to the student)

A benchmark task is a small, self-contained research problem that an AI agent attempts on its own, inside a sealed computer (a Docker **container**). It has four parts:

1. **Instruction**: what the agent is asked to do, written like a note to an expert colleague.
2. **Environment**: the container, with software and data, that the agent works in.
3. **Reference solution** (the **oracle**): your own solution. It proves the task can be solved.
4. **Verifier**: tests that check the agent's output files in a *separate*, clean container. The result is a **reward**: 1 if everything passes, 0 otherwise.

A task is **valid** when the oracle scores 1 and an agent that does nothing scores 0. It is **good** when a real expert could solve it from the instruction alone, and passing really means the science was done right. It is **hard** when today's best agents fail for real scientific reasons.

### Glossary (define each the first time it comes up)
- **Container:** a sealed, reproducible mini-computer built from a `Dockerfile`.
- **Oracle:** the reference solution, run as if it were an agent.
- **Nop agent:** an "agent" that does nothing. It must score 0; otherwise the task gives free points.
- **Verifier:** the tests that grade the output.
- **Artifact:** an output file the agent writes, which gets copied to the verifier.
- **Reward:** the grade, 1 or 0.
- **Trajectory:** the full record of what an agent did: its thoughts, commands and outputs.
- **Fork:** the student's own copy of the class repository on GitHub.
- **Pull request (PR):** a request to merge their work into the class repository.
- **CI:** the automatic checks GitHub runs on every PR.
- **Canary line:** the `harbor-canary GUID …` comment at the top of task files. It marks the files as benchmark data that must never be used to train AI models. Keep it in every file.

## The goal: this week and this quarter

| Level | Name | Means | When |
|---|---|---|---|
| **1** | **Ambitious** | The hardest task you can think of in your field, in Harbor format. A top expert could do it, and you expect frontier agents to fail. The oracle scores 1, nop scores 0, CI passes. The acceptance window has an honest justification. Submitted as a pull request. | **Week 1 homework, due before class on Wed Oct 7** |
| 2 | Honest | You read agents' full trajectories and fixed everything they exposed: ambiguities, leaks, windows that reject good answers. Tolerances are calibrated with a script. | mid-quarter |
| 3 | Proven hard | Frontier agents fail across several runs, and the trajectories show they fail on the science, not on a gap in your task. | late quarter |
| 4 | Benchmark-ready | Meets the [Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science) bar and could be proposed there. | end of quarter |

**Aim high from week 1.** An easy task misses the point of the assignment; push the student toward the hardest problem they can still verify. The difficulty should be *real*: expert knowledge, long pipelines, messy real data. It should never be artificial, like obscure wording or trick formats. What week 1 does *not* need is polish: the task must be valid, but making it airtight is levels 2–3. Don't pull a calibration script into week 1 unless they want to.

## Step 0: Set up

Nothing runs the task on this computer, so no Docker or Harbor is needed. The student needs git, a GitHub account, the GitHub CLI and uv; all work on macOS, Linux and Windows.

1. **uv** runs the class's Python tools without installing anything system-wide. Check `uv --version`. If it's missing, install it, then open a new terminal (or use the full path the installer prints):
   - macOS or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Then run `uv run tools/hw.py`. Setup is GitHub, first and only:
   - It checks that the **GitHub CLI** (gh) is installed, and installs it or tells the student how.
   - The student logs in, once: **(student runs this)** `gh auth login --hostname github.com --git-protocol https --web`. It shows a one-time code, which they enter at github.com/login/device.
   - Ask the student whether the account gh shows is theirs. If it is, record it: `uv run tools/hw.py confirm <github-username>`. If it isn't (someone else's login on a shared computer), they log out with `gh auth logout` and log in as themselves.

   Explain in one line: **git** keeps versions of files, **GitHub** hosts them, and **gh** connects the two, so submitting is one command.

On Windows, run everything in PowerShell or Windows Terminal. The student's approvals need a real terminal window.

## Step 1: Find the hardest task (CHECKPOINT)

Interview them. Ask one or two questions at a time, not a questionnaire, and push toward ambition.

- What is their research area? What is the **hardest thing they, or the best people in their field, do on a computer** that still ends in an answer that can be checked?
- What took them weeks to learn to do right? Where do smart newcomers go wrong without noticing?
- What would genuinely impress them if an AI could do it on its own?
- Do they have a solved instance? For example a result from their own paper or thesis, or a published analysis they can reproduce. That becomes the reference answer.
- Can the inputs be shared publicly? They must be public, synthetic, or generated by a script. Keep them under 20 MB; a small real subset beats a large toy set. Never use unpublished collaborator data without permission, and never use personal or medical data.

Then propose **two or three concrete task ideas** drawn from their answers. For each, give in one line each: what the agent is given, what it must produce (a file with a specific format), how the verifier will check it, and **why a frontier agent would likely fail**. Use this frame for difficulty: it's a pair, **what the solver must deliver × what the data withholds**.
- Deliver more: not "compute X", but find which quantity matters, measure the system's own parameters, or produce a full pipeline's final product.
- Withhold more: don't give the method, the fitting range or the model; use real instrument data with its gaps, artifacts and systematics; build a long pipeline where an early mistake silently corrupts the final answer.

The task must still be:
- **Verifiable by a program:** a number in a window, a set of detected events, fitted parameters, a file with required properties. Not an opinion or prose.
- **Solvable by a top expert** from the instruction and data alone, with a reference answer you trust.
- **Hard for the right reason:** expertise, realism and length, never trick wording.
- **Runnable in the class's checks:** no GPU, at most 4 CPUs and 8 GB of memory. The agent may take hours, but the reference answer can be precomputed (see Step 3c).
- **Not a famous number** an agent could recall instead of computing (see Step 3e).

**CHECKPOINT:** the student picks one idea and a short task name: lowercase words joined by hyphens. Confirm in four sentences what goes in, what comes out, how it's checked, and why it's hard. Then run `uv run tools/hw.py new <task-name>`.

## Step 2: The new folder

`uv run tools/hw.py new` creates `week-1/submissions/<github-username>/<task-name>/` on its own branch, `week1-<task-name>`. It copies the class templates, in Harbor's task format with a separate offline verifier, plus the README sections and `authoring/attempts.md`, and fills in the student's name, GitHub username and GitHub's private email address in `task.toml`. Walk the student through the new folder: which part is which of the four parts.

## Step 3: Build the four parts

The containers only ever run on GitHub and on the instructor's machine, never here. So write each file carefully, and check the logic you can on this computer: run the solution's Python on the data with uv (pointed at the local copy of the data), then run the tests' checks on its output.

### 3a. Data and environment (`environment/`)
- Put input files in `environment/data/`, and in `environment/Dockerfile` add `COPY data /root/data`.
- If data is generated, put the generator in `authoring/provenance/`. Make it deterministic (fixed random seed). Nothing in `authoring/` is ever shown to the agent.
- Start from a small official image (`python:3.11-slim`, or `ubuntu:24.04`). Install `curl` and `ca-certificates`, which agent installers need. **Pin** Python packages (`numpy==2.1.3`); don't pin apt packages.
- To run Python on the laptop (to generate data or try the solution), use the same pinned packages through uv, e.g. `uv run --with numpy==2.1.3 --with scipy==1.14.1 python script.py`. Don't install packages into the system Python.
- Nothing in the environment may contain or hint at the answer: no solution files, no expected outputs, no telling file names.

### 3b. The instruction (`instruction.md`), CHECKPOINT
This is the scientific heart. **The student writes it, or rewrites your draft in their own words and approves every sentence.** Terminal-Bench-Science requires instructions written by the domain expert. Help them check it:
- Test: could an independent expert in their field solve the task from this text alone?
- Use absolute paths for every input and output (`/root/data/…`, `/root/results/…`), and give the exact output format (JSON keys, CSV columns, units). List the output files in `artifacts` in `task.toml` now: the instruction and the verifier share them.
- Where competent experts could reasonably differ, say which convention to use: units, sign, normalization, frequency range, index origin. Leave out what is standard practice; it's a note to a colleague, not a tutorial.
- Don't reveal the method unless the method is part of the specification.
- It must end with exactly this line, where N is `[agent] timeout_sec` in `task.toml`. Choose a time a strong expert would need, with margin: from 600 up to 18000 seconds (5 hours).
  `You have N seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.`
- When it's ready, the student reads it in full and approves it: **(student runs this)** `uv run tools/hw.py approve instruction`. If the instruction changes later, even by one word, they approve it again.

### 3c. Reference solution (`solution/`)
`solution/solve.sh` must produce the graded output files. There are two ways to do it:
- **Compute it:** run `python3 /solution/solve.py` on the inputs. Best when the computation takes minutes.
- **Ship the reference:** for hard tasks whose real computation takes hours or needs the student's research code, run that computation once on their machine. Put the outputs in `solution/data/`, and have `solve.sh` copy them to the artifact paths. Record exactly how they were produced in `authoring/provenance/`: code and version, command, inputs, date. The student must trust these numbers; they are the answer key.

Either way, the student should understand the method and agree it's how an expert would do it.

### 3d. The verifier (`tests/`)
- It runs in a **separate container** with **no network**. It sees only the files listed in `artifacts` in `task.toml`, copied to the same paths. Every package the tests import must be installed in `tests/Dockerfile`, and every artifact's parent folder created there with `RUN mkdir -p …`.
- Write pytest checks in `tests/test_*.py`. Each test checks **one observable against one rule**: the file exists and parses, a value is finite, a value is inside the accepted window. Use informative failure messages, but never print the expected answer.
- Check the **outcome**, not the method. Don't check which library was used.
- The expected answers live only in `tests/`, never in `environment/` or in the instruction.
- Keep `tests/test.sh` from the template. It runs every test and writes the reward.
- Make sure the answers that should fail really fail: a wrong method, a textbook value, an empty or malformed file.

### 3e. The acceptance window (CHECKPOINT)
A tolerance is fair only if good methods pass and wrong ones fail. **The student decides the window.** For week 1:
- Write two or three sentences in the README's Verification section: why this window? Which reasonable choices (a different window function, fitting method or bin size) still land inside it?
- **Don't ask for a famous number.** If the answer is a textbook constant (−5/3, 5/3, 2.0, 1 AU), an agent can pass by recalling it without doing the work. Check that the textbook guess falls *outside* the window; if it doesn't, choose data whose true answer is away from the default.
- Level 2 turns this into a script (`authoring/evidence/calibrate.py`) that runs several good and wrong methods. It's optional in week 1.
- Then the student reviews the tests and the Verification section, and approves: **(student runs this)** `uv run tools/hw.py approve window`.

### 3f. Metadata and write-up
- `task.toml`: fill every `[metadata]` field (including a real `expert_time_estimate_hours`), and the `[task]` description and keywords.
- `README.md`: a few real sentences for each of the three sections (Difficulty, Reference solution, Verification).

## Step 4: Submit (CHECKPOINT: pushing is public)

1. **CHECKPOINT:** the student approves publishing: **(student runs this)** `uv run tools/hw.py approve publish`. It lists every file that will become public, and asks them to confirm the data may be shared and to accept the MIT license.
2. Ask the student which AI agent(s) helped build the task, and how, in a sentence or two. Then run `uv run tools/hw.py submit --ai "<their answer>"`. It makes the student's own copy of the repository on GitHub (a **fork**: a pull request has to come from a copy they own), sets commits to use GitHub's private email address, checks that the branch changes only their folder, commits, pushes, and opens the pull request with the class template filled in. `--dry-run` shows what it would do without doing it.
3. Changes after that: the student approves publishing again, and `uv run tools/hw.py submit` pushes them. The pull request updates by itself.
4. When the pull request opens, GitHub checks the task: the reference solution must score 1 and an agent that does nothing must score 0. For a first-time contributor, GitHub holds the run until the instructor approves it, so "awaiting approval" is expected. Tell the student, and don't wait in a loop. `uv run tools/hw.py` shows the result the next time it runs. If the check failed, it shows how to read the log: read it together, fix the task, and submit again.
5. That's the end of week 1. The instructor runs frontier agents on every task.

By submitting, the student licenses their task under the repository's MIT license. Confirm the data is theirs to share, or openly licensed; if it came from a public archive, name the source in the README.

## Later in the quarter: climbing the ladder

When the student comes back to improve their task, run `uv run tools/hw.py`, then read `authoring/attempts.md` and the task's `class_level`.

- **To reach level 2 (honest):** read the whole trajectory of each frontier agent run on the task (the instructor runs them). Ask:
  - Did it fail only because the instruction was ambiguous?
  - Could it pass without doing the science: by guessing, writing a plausible default, reading something it shouldn't, or fetching this public repository, where `tests/` and the README reveal the answer?
  - Did the verifier reject an answer an expert would accept?

  Fix the task, not the agent. Write `authoring/evidence/calibrate.py` and keep the window honest with it.
- **To reach level 3 (proven hard):** confirm across several runs, ideally by more than one agent, that the failures are on the science. If agents succeed, raise the difficulty where it's essential, never where it's arbitrary: deliver more, or withhold more (the frame from Step 1). Keep it verifiable and deterministic.
- **To reach level 4 (benchmark-ready):** read Terminal-Bench-Science's `CONTRIBUTING.md` and `rubrics/`, and check the task against them. Then consider proposing the task there. Accepted tasks earn co-authorship on their paper.

## Hard rules

- Only change files under `week-1/submissions/<github-username>/`. Never edit another student's task, the tools or the templates in a PR.
- Never put answers where the agent can see them: not in `environment/`, not in the instruction, not in file names.
- Never run the student-at-the-keyboard commands yourself, and never let a secret appear in this conversation or in git. If a secret was ever committed, it must be revoked with the provider; deleting the file doesn't make it safe.
- Never edit `authoring/progress.json`, and never run `uv run tools/hw.py approve` for the student or feed it input.
- Only use data the student is allowed to share publicly.
- Report honestly. Never edit a reward, fake an attempt, or claim a run you didn't do.
