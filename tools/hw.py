# /// script
# requires-python = ">=3.11"
# ///
"""The homework bookkeeper. It checks the setup and your task, prints a checklist, and ends with
exactly one NEXT step that says who does it: the agent, the student, or both together.

Run from the repository root, on macOS, Linux or Windows (any shell, PowerShell included):
    uv run tools/hw.py                                     the checklist and the next step
    uv run tools/hw.py plan                                what happens, start to finish (show the student first)
    uv run tools/hw.py new <task-name>                     create your task folder and its branch
    uv run tools/hw.py check [task-folder]                 the static checks CI runs, grouped by step
    uv run tools/hw.py approve instruction|window|publish  the student signs off, in their own terminal
    uv run tools/hw.py note "<where we are, what's next>"  leave a note for the next session
    uv run tools/hw.py submit --ai "<which AI helped>"     commit, push and open the pull request

Students never run a task: no Docker or Harbor is needed here. When the pull request opens, CI checks
that the reference solution scores 1 and doing nothing scores 0, and the instructor runs frontier
agents. Progress is worked out from the files every time; approvals are stored in the task's
authoring/progress.json with a fingerprint of the files they covered, so any later change shows up.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
CLASS_REPO = "huangzesen/ai-in-research-homework"
CLASS_OWNER, REPO_NAME = CLASS_REPO.split("/")
WEEK = os.environ.get("WEEK", "week-1")
WEEK_N = WEEK.split("-")[-1]
BRANCH_PREFIX = f"week{WEEK_N}-"
PROGRESS = "authoring/progress.json"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STATUS_TEMPLATE = "Where the task stands and what's next"
HW = "uv run tools/hw.py"
WINDOWS = os.name == "nt"
# templates/ file -> where it goes in a new task
SCAFFOLD = {
    "instruction.md": "instruction.md",
    "README.md": "README.md",
    "attempts.md": "authoring/attempts.md",
    "environment/Dockerfile": "environment/Dockerfile",
    "solution/solve.sh": "solution/solve.sh",
    "tests/Dockerfile": "tests/Dockerfile",
    "tests/test.sh": "tests/test.sh",
    "tests/test_outputs.py": "tests/test_outputs.py",
}


# ---------------------------------------------------------------- small helpers

def run(cmd, timeout=30):
    """Runs a command in the repository. Returns (exit code, stdout, stderr); 127 if not installed."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")  # fail fast instead of waiting for a password
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", ""
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"


def git(*args):
    return run(["git"] + list(args))[1]


def show(path):
    """A path for humans: ~/... when it's under the home folder (the full path on Windows)."""
    path = Path(path).resolve()
    if WINDOWS:
        return str(path)
    try:
        return "~/" + path.relative_to(HOME).as_posix()
    except ValueError:
        return str(path)


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def write(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="minutes")


def today():
    return datetime.date.today().isoformat()


def section(text, heading):
    """The body of a `## heading` section without HTML comments, or None if there is none."""
    match = re.search(r"^" + re.escape(heading) + r"[ \t]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return re.sub(r"<!--.*?-->", "", match.group(1), flags=re.S).strip() if match else None


def system():
    if WINDOWS:
        return "Windows"
    return "macOS" if sys.platform == "darwin" else "Linux"


def student_cmd(sub):
    """A command the student types in their own terminal: go to the repository, then run tools/hw."""
    if WINDOWS:  # PowerShell 5 has no &&
        return f'cd "{ROOT}"; {HW} {sub}'
    return f"cd {shlex.quote(show(ROOT)) if ' ' in show(ROOT) else show(ROOT)} && {HW} {sub}"


def github_repo(url):
    """(owner, name) of a GitHub remote URL, or (None, None)."""
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url or "")
    return (match.group(1), match.group(2)) if match else (None, None)


def remote_urls():
    """{remote name: URL} as written in the git config."""
    urls = {}
    for line in git("config", "--get-regexp", r"^remote\..*\.url$").splitlines():
        key, _, url = line.partition(" ")
        urls[key[len("remote."):-len(".url")]] = url.strip()
    return urls


# ---------------------------------------------------------------- what to do next

class Next:
    WHO = {
        "you": ("NEXT (you, the agent)", f"Then run {HW} again."),
        "student": ("NEXT (the student, in their own terminal window; never run it for them)",
                    f"Wait until they say it's done, then run {HW} again."),
        "together": ("NEXT (you and the student, together)", f"Then run {HW} again."),
        "done": ("DONE", ""),
    }

    def __init__(self, who, text, cmds=(), details=(), step=None):
        self.who, self.text, self.cmds, self.details, self.step = who, text, list(cmds), list(details), step

    def show(self):
        title, then = self.WHO[self.who]
        print(title + (f"   SKILL.md {self.step}" if self.step else ""))
        print(textwrap.fill(self.text, 100, initial_indent="  ", subsequent_indent="  "))
        for line in self.details:
            print("    " + line)
        for cmd in self.cmds:
            print("      " + cmd)
        if then:
            print("  " + then)


class Item:
    def __init__(self, key, ok, label, nxt=None):
        self.key, self.ok, self.label, self.next = key, ok, label, nxt


def fix_list(problems, limit=4):
    lines = []
    for message, hint in problems[:limit]:
        lines.append("- " + message)
        lines += ["  -> " + h.strip() for h in hint.splitlines() if h.strip()]
    if len(problems) > limit:
        lines.append(f"- and {len(problems) - limit} more: {HW} check")
    return lines


# ---------------------------------------------------------------- setup: git, GitHub, the fork

class Ctx:
    def __init__(self):
        self.system = system()
        code, top, _ = run(["git", "rev-parse", "--show-toplevel"])
        self.git = code == 0 and Path(top).resolve() == ROOT
        self.branch = git("branch", "--show-current") if self.git else ""
        self.user = None
        self.class_remote = None
        self._pr = False

    @property
    def login(self):
        return (self.user or {}).get("login", "")

    def state_path(self):
        code, gitdir, _ = run(["git", "rev-parse", "--absolute-git-dir"])
        return Path(gitdir) / "hw.json" if code == 0 else None

    def local_state(self):
        path = self.state_path()
        try:
            return json.loads(read(path)) if path else {}
        except ValueError:
            return {}

    def save_local_state(self, state):
        path = self.state_path()
        if path:
            write(path, json.dumps(state, indent=2) + "\n")

    def base_ref(self):
        """The class repository's main branch, as this clone knows it."""
        if self.class_remote and run(["git", "rev-parse", "--verify", "-q", f"{self.class_remote}/main"])[0] == 0:
            return f"{self.class_remote}/main"
        return "HEAD"


def check_where(c):
    if not c.git:
        return False, "a git clone of the class repository", Next(
            "you", "This folder isn't a git clone of the class repository. Clone it in the home folder and continue "
            "there:", [f"cd ~ && git clone https://github.com/{CLASS_REPO}.git && cd {REPO_NAME}"
                       if not WINDOWS else f"cd ~; git clone https://github.com/{CLASS_REPO}.git; cd {REPO_NAME}"])
    return True, f"{c.system}; repository at {show(ROOT)}", None


def check_gh(c):
    code, out, _ = run(["gh", "--version"])
    if code == 0:
        version = re.search(r"\d+\.\d+\.\d+", out)
        return True, "GitHub CLI (gh) " + (version.group(0) if version else ""), None
    why = "Install the GitHub CLI (gh). It makes forking and pull requests one command each."
    if c.system == "Windows":
        return False, "GitHub CLI (gh)", Next(
            "student", why + " Run this in PowerShell, then close and reopen the terminal and restart the coding "
            "agent, so both find gh:", ["winget install --id GitHub.cli -e"])
    if c.system == "macOS" and shutil.which("brew"):
        return False, "GitHub CLI (gh)", Next("you", why, ["brew install gh"])
    if c.system == "macOS":
        return False, "GitHub CLI (gh)", Next("student", why + " Download the macOS installer from https://cli.github.com and open it.")
    if shutil.which("apt-get"):
        return False, "GitHub CLI (gh)", Next("student", why + " It asks for their computer password:",
                                              ["sudo apt-get update && sudo apt-get install -y gh"])
    return False, "GitHub CLI (gh)", Next("student", why + " See https://github.com/cli/cli#installation")


def check_login(c):
    """Logged in to GitHub, and as whom. The answer is cached in .git/hw.json per login token (only a
    hash of the token is kept), so most runs make no network call."""
    login = Next("student", "Log in to GitHub. No account yet? Create one first at https://github.com/signup. Then run "
                 "the command below, accept the defaults, and approve in the browser. If no browser opens, go to "
                 "https://github.com/login/device and type the code it shows.",
                 ["gh auth login --hostname github.com --git-protocol https --web"], step="Step 0")
    code, token, err = run(["gh", "auth", "token", "--hostname", "github.com"])
    if code != 0 and "unknown" not in err:
        return False, "logged in to GitHub", login
    key = hashlib.sha256(token.encode()).hexdigest()[:12] if code == 0 else ""
    state = c.local_state()
    if key and state.get("github_user", {}).get("token") == key:
        c.user = state["github_user"]
        return True, f"logged in to GitHub as {c.login}", None
    code, out, err = run(["gh", "api", "user"])
    if code != 0:
        if "rate limit" in err.lower():
            return False, "logged in to GitHub", Next(
                "you", "GitHub's API limit for this login is used up for now; another tool may be using it. Wait a few "
                "minutes and try again.")
        if "401" in err or "credentials" in err.lower() or "auth login" in err:
            login.text = "The GitHub login has expired. " + login.text
            return False, "logged in to GitHub", login
        return False, "logged in to GitHub", Next(
            "you", f"GitHub didn't answer ({(err.splitlines() or [''])[0]}). Check the internet connection.")
    user = json.loads(out)
    c.user = {"login": user["login"], "id": user["id"], "name": user.get("name") or "", "token": key}
    if key:
        state["github_user"] = c.user
        c.save_local_state(state)
    return True, f"logged in to GitHub as {c.login}", None


def check_identity(c):
    name, email = git("config", "user.name"), git("config", "user.email")
    if name and email:
        public = "" if email.endswith("@users.noreply.github.com") else " (this email is public in commits)"
        return True, f"git identity: {name} <{email}>{public}", None
    if not email and not c.user:
        return None, "git identity for commits", None
    text = ("Set the name and email git records in each commit, for this repository only. The email is GitHub's "
            "private address, which keeps their real one off the public record.")
    who, cmds = "you", []
    if not name:
        if (c.user or {}).get("name"):
            cmds.append(f'git config user.name "{c.user["name"]}"')
        else:
            who, text = "together", text + " Ask the student how their name should appear."
            cmds.append('git config user.name "Their Name"')
    if not email:
        cmds.append(f"git config user.email {c.user['id']}+{c.login}@users.noreply.github.com")
    return False, "git identity for commits", Next(who, text, cmds)


def check_fork(c):
    remotes = remote_urls()
    for remote, url in remotes.items():
        if "/".join(github_repo(url)).lower() == CLASS_REPO.lower():
            c.class_remote = remote
    owner, name = github_repo(remotes.get("origin"))
    if owner and owner.lower() == c.login.lower():
        if not c.class_remote:
            return False, "the class repository as `upstream`", Next(
                "you", "Add the class repository as `upstream`, so the tools can compare against it:",
                [f"git remote add upstream https://github.com/{CLASS_REPO}.git", "git fetch upstream"])
        label = f"your fork: {owner}/{name}" if owner.lower() != CLASS_OWNER else f"the class repository ({owner}/{name})"
        return True, label, None
    cmds = ["gh repo fork --remote"]
    if "origin" not in remotes:
        cmds.insert(0, f"git remote add origin https://github.com/{CLASS_REPO}.git")
    return False, "your own fork on GitHub", Next(
        "you", "Make the student's own copy of the repository on GitHub (a fork) and point this clone at it. "
        "Their fork becomes `origin`, the class repository `upstream`.", cmds, step="Step 0")


def check_push(c):
    url = remote_urls().get("origin", "")
    if url.startswith(("git@", "ssh://")):
        _, _, err = run(["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "git@github.com"], timeout=20)
        if "successfully authenticated" in err:
            return True, "git can push to GitHub (SSH)", None
        return False, "git can push to GitHub", Next(
            "you", "origin uses SSH, but GitHub doesn't accept this machine's SSH key. Switch it to HTTPS with the "
            "GitHub login:", [f"git remote set-url origin https://github.com/{c.login}/{github_repo(url)[1]}.git",
                              "gh auth setup-git"])
    helpers = run(["git", "config", "--get-regexp", r"^credential\..*helper$"])[1]
    if "auth git-credential" in helpers:
        return True, "git can push to GitHub", None
    return False, "git can push to GitHub", Next("you", "Let git push with the GitHub login:", ["gh auth setup-git"])


SETUP = [
    ("where", check_where, "a git clone of the class repository", ()),
    ("gh", check_gh, "GitHub CLI (gh)", ("where",)),
    ("login", check_login, "logged in to GitHub", ("gh",)),
    ("identity", check_identity, "git identity for commits", ("where",)),
    ("fork", check_fork, "your own fork on GitHub", ("login",)),
    ("push", check_push, "git can push to GitHub", ("fork",)),
]


def setup_items(c):
    items, ok = [], {}
    for key, check, label, needs in SETUP:
        if all(ok.get(n) for n in needs):
            items.append(Item(key, *check(c)))
        else:
            items.append(Item(key, None, label))
        ok[key] = items[-1].ok
    return items


def require_setup(c):
    for item in setup_items(c):
        if not item.ok:
            print("Finish setup first.\n")
            (item.next or Next("you", f"Run {HW} to see what's missing.")).show()
            sys.exit(1)


# ---------------------------------------------------------------- the task

TASK_STEPS = [
    ("branch", "folder and branch"),
    ("environment", "data and environment"),
    ("instruction", "instruction"),
    ("approve-instruction", "the student approved the instruction"),
    ("solution", "reference solution"),
    ("tests", "verifier tests"),
    ("window", "the student approved the acceptance window"),
    ("metadata", "task.toml metadata and README"),
    ("publish", "the student approved publishing"),
    ("pr", "pull request open"),
]


def find_task(c):
    """The task being worked on: the one named by the branch, else the student's only task."""
    base = ROOT / WEEK / "submissions" / c.login
    tasks = sorted(p.parent for p in base.glob("*/task.toml")) if c.login and base.is_dir() else []
    if c.branch.startswith(BRANCH_PREFIX) and (base / c.branch[len(BRANCH_PREFIX):] / "task.toml").is_file():
        return base / c.branch[len(BRANCH_PREFIX):], tasks
    return (tasks[0] if len(tasks) == 1 else None), tasks


def scaffold(task, login, author, email):
    """A new task folder from templates/, in Harbor's task format."""
    templates = ROOT / "templates"
    for src, dst in SCAFFOLD.items():
        (task / dst).parent.mkdir(parents=True, exist_ok=True)
        write(task / dst, read(templates / src))
    for folder in ("environment/data", "authoring/provenance", "authoring/evidence"):
        (task / folder).mkdir(parents=True, exist_ok=True)
    for script in ("solution/solve.sh", "tests/test.sh"):
        try:
            os.chmod(task / script, 0o755)
        except OSError:
            pass  # Harbor marks the scripts executable itself
    toml = read(templates / "task.toml")
    for marker, value in (("@TASK_NAME@", task.name), ("@GITHUB_USERNAME@", login),
                          ("@AUTHOR_NAME@", json.dumps(author, ensure_ascii=False)),
                          ("@AUTHOR_EMAIL@", json.dumps(email, ensure_ascii=False))):
        toml = toml.replace(marker, value)
    write(task / "task.toml", toml)


def lint(task):
    """The static checks, grouped by part."""
    sys.path.insert(0, str(ROOT / "tools"))
    import check_task
    del check_task.failures[:], check_task.warnings[:]
    check_task.check(Path(task).resolve())
    groups = {part: [] for part in check_task.PARTS}
    for part, message, hint in check_task.failures:
        groups[part].append((message, hint))
    return groups, [(m, h) for _, m, h in check_task.warnings], check_task


def task_files(task, *subpaths):
    """Files git would publish under these subpaths of the task (all of it if none), minus progress.json."""
    task = Path(task).resolve()
    targets = [rel(task / s) for s in subpaths] or [rel(task)]
    out = run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--"] + targets)[1]
    files = sorted(set(f for f in out.splitlines() if f))
    return [f for f in files if f != rel(task / PROGRESS)]


def fingerprint(task, *subpaths, extra=""):
    """A short hash of the files; the session note in attempts.md doesn't count, so notes never undo approvals.
    Line endings don't count either, so a Windows editor re-saving a file doesn't undo an approval."""
    h = hashlib.sha256()
    for name in task_files(task, *subpaths):
        path = ROOT / name
        content = path.read_bytes().replace(b"\r\n", b"\n") if path.is_file() else b"(deleted)"
        if name.endswith("authoring/attempts.md"):
            content = re.sub(rb"(?ms)^## Status[ \t]*\n.*?(?=^## |\Z)", b"", content)
        h.update(name.encode() + b"\0" + content + b"\0")
    h.update(extra.encode())
    return h.hexdigest()[:16]


def window_fingerprint(task):
    tests = [rel(p)[len(rel(task)) + 1:] for p in sorted((Path(task) / "tests").glob("test_*.py"))]
    return fingerprint(task, *tests, extra=section(read(Path(task) / "README.md"), "## Verification") or "")


def load_progress(task):
    try:
        return json.loads(read(Path(task) / PROGRESS) or "{}")
    except ValueError:
        return {}


def save_progress(task, progress):
    progress["about"] = "Written by tools/hw: fingerprints of what the student approved. Don't edit by hand."
    path = Path(task) / PROGRESS
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, json.dumps(progress, indent=2, sort_keys=True) + "\n")


def status_note(task):
    note = section(read(Path(task) / "authoring/attempts.md"), "## Status") or ""
    return "" if not note or note.startswith(STATUS_TEMPLATE) else note


def find_pr(c, branch):
    """The open (else merged) pull request from this branch: a dict, None if there is none, False if unknown."""
    code, out, _ = run(["gh", "pr", "list", "--repo", CLASS_REPO, "--head", branch, "--author", c.login,
                        "--state", "all", "--json", "number,url,state", "--limit", "20"])
    if code != 0:
        return False
    prs = json.loads(out or "[]")
    for state in ("OPEN", "MERGED"):
        for pr in prs:
            if pr.get("state") == state:
                return pr
    return None


def pr_checks(pr):
    """'passed', 'failed', or 'waiting' for the class checks on a pull request."""
    code, out, _ = run(["gh", "pr", "view", str(pr["number"]), "--repo", CLASS_REPO, "--json", "statusCheckRollup"])
    if code != 0:
        return "waiting"
    checks = json.loads(out or "{}").get("statusCheckRollup") or []
    results = [(ch.get("conclusion") or ch.get("state") or "").upper() for ch in checks]
    if any(r in ("FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE") for r in results):
        return "failed"
    if results and all(r in ("SUCCESS", "NEUTRAL", "SKIPPED") for r in results):
        return "passed"
    return "waiting"


def approve_next(what, progress):
    before = progress.get(what, {}).get("approved")
    change = {"instruction": "The instruction", "window": "The tests or the README's Verification section",
              "publish": "The task"}[what]
    text = {"instruction": "Ask the student to read the instruction and approve it, in their own terminal:",
            "window": "Ask the student to review the acceptance window (the tests and the README's Verification "
                      "section) and approve it, in their own terminal:",
            "publish": "Everything is ready. Ask the student to review what will become public and approve it, in "
                       "their own terminal:"}[what]
    if before:
        text = f"{change} changed after the student approved it ({before[:10]}). " + text
    if WINDOWS:
        text += " (PowerShell or Windows Terminal)"
    step = {"instruction": "Step 3b", "window": "Step 3e", "publish": "Step 4"}[what]
    return Next("student", text, [student_cmd(f"approve {what}")], step=step)


def task_items(c, task, check_pr=True):
    groups, _, _ = lint(task)
    progress = load_progress(task)
    branch = BRANCH_PREFIX + Path(task).name
    items = []

    def add(key, ok, label, nxt=None):
        items.append(Item(key, ok, label, nxt))

    def part(key, parts, label, who, text, step):
        problems = [p for name in parts for p in groups[name]]
        add(key, not problems, label, Next(who, text + " Still to fix:", details=fix_list(problems), step=step) if problems else None)

    # 1. folder and branch, file sizes and secrets
    if c.branch != branch:
        exists = run(["git", "rev-parse", "--verify", "-q", "refs/heads/" + branch])[0] == 0
        add("branch", False, f"folder and branch {branch}", Next(
            "you", f"Work on this task's own branch (now on {c.branch or 'no branch'}):",
            [f"git switch {branch}" if exists else f"git switch -c {branch}"]))
    else:
        part("branch", ("layout", "files"), f"folder {rel(task)}, branch {branch}", "you", "Fix the task folder.", None)

    # 2-8. build the four parts; the student approves the instruction and the window
    part("environment", ("environment",), "data and environment", "you",
         "Build the data and the agent's container.", "Step 3a")
    part("instruction", ("instruction",), "instruction", "together",
         "Write the instruction. The student writes it, or rewrites your draft in their own words.", "Step 3b")
    if items[-1].ok:
        ok = progress.get("instruction", {}).get("fingerprint") == fingerprint(task, "instruction.md")
        add("approve-instruction", ok, "the student approved the instruction", None if ok else approve_next("instruction", progress))
    else:
        add("approve-instruction", None, "the student approved the instruction")
    part("solution", ("solution",), "reference solution", "you", "Write the reference solution.", "Step 3c")
    part("tests", ("tests",), "verifier tests", "you", "Write the verifier's tests.", "Step 3d")
    if items[-1].ok and not groups["window"]:
        ok = progress.get("window", {}).get("fingerprint") == window_fingerprint(task)
        add("window", ok, "the student approved the acceptance window", None if ok else approve_next("window", progress))
    elif items[-1].ok:
        part("window", ("window",), "the student approved the acceptance window", "together",
             "Choose the acceptance window with the student, and write why in the README's Verification section.", "Step 3e")
    else:
        add("window", None, "the student approved the acceptance window")
    part("metadata", ("metadata", "readme"), "task.toml metadata and README", "you",
         "Fill in task.toml's [task] and [metadata] fields, and the README.", "Step 3f")

    # 9. the student approved publishing exactly these files
    if all(i.ok for i in items):
        ok = progress.get("publish", {}).get("fingerprint") == fingerprint(task)
        add("publish", ok, "the student approved publishing", None if ok else approve_next("publish", progress))
    else:
        add("publish", None, "the student approved publishing")

    # 10. the pull request, and what CI said about it
    if not all(i.ok for i in items) or not check_pr:
        add("pr", None, "pull request open")
        return items
    pr = find_pr(c, branch)
    c._pr = pr
    if pr is False:
        add("pr", False, "pull request open", Next("you", "Couldn't ask GitHub about pull requests. Check the internet connection."))
    elif pr is None:
        add("pr", False, "pull request open", Next(
            "together", "Ask the student which AI agent(s) helped build the task, and how, in a sentence or two. "
            "Then commit, push and open the pull request:", [f'{HW} submit --ai "<their answer>"'], step="Step 4"))
    elif pr["state"] == "MERGED":
        add("pr", True, f"pull request merged: {pr['url']}")
    else:
        dirty = git("status", "--porcelain", "--", rel(task))
        ahead = run(["git", "rev-list", "--count", f"origin/{branch}..HEAD"])
        checks = pr_checks(pr)
        c._pr = dict(pr, checks=checks)
        if dirty or ahead[0] != 0 or ahead[1] != "0":
            add("pr", False, f"pull request open: {pr['url']}", Next(
                "you", "Push the latest changes to the open pull request:", [f"{HW} submit"], step="Step 4"))
        elif checks == "failed":
            add("pr", False, f"pull request open: {pr['url']}, but the class checks failed", Next(
                "together", "GitHub ran the task and it failed: the reference solution must score 1 and doing nothing "
                "0. Read why, fix the task, and submit again (the student approves the changes first):",
                [f"gh pr checks {pr['number']} --repo {CLASS_REPO}",
                 f"gh run view <run-id from the line above> --repo {CLASS_REPO} --log-failed"], step="Step 4"))
        else:
            add("pr", True, f"pull request open: {pr['url']}" + (", checks passed" if checks == "passed" else ""))
    return items


# ---------------------------------------------------------------- uv run tools/hw.py (status)

PLAN = f"""\
PLAN: what happens, start to finish. Show this to the student before anything else.

  1. Set up (once). The agent checks git and GitHub and fixes what's missing. You do one
     thing yourself, in your own terminal: log in to GitHub.
  2. Choose the task. The agent asks about your research, and together you pick the hardest
     problem in your field that a program can still check.
  3. Build it. The agent writes the container, the reference solution and the tests. You write
     the instruction (or rewrite the agent's draft) and decide what counts as a right answer.
  4. Submit. You check what will become public, and the agent opens your pull request. That's
     the end of week 1. From there the instructor runs everything: GitHub checks that your
     reference solution passes and doing nothing fails, then frontier AI agents try your task.

  You sign off three times by typing "yes" in your own terminal: the instruction, the
  acceptance window, and publishing. Nothing of yours is public before the last one.
  All of it usually takes a few sessions of 1-2 hours. Run {HW} any time to see
  where you are."""


def cmd_plan(args):
    print(PLAN)


def mark(item, first):
    return "[x]" if item.ok else ("[!]" if item is first else "[ ]")


def status(c=None):
    c = c or Ctx()
    setup = setup_items(c)
    ready = all(i.ok for i in setup if i.key in ("where", "gh", "login", "fork"))
    task, tasks = find_task(c) if ready else (None, [])

    print(f"Homework bookkeeper, {WEEK}. Run every command from {show(ROOT)}.")
    if not task and not tasks:
        print("\n" + PLAN)
    note = status_note(task) if task else ""
    if note:
        print("\nLast session's note:")
        print(textwrap.fill(note, 100, initial_indent="  ", subsequent_indent="  "))

    first_setup = next((i for i in setup if i.ok is False), None)
    print("\nSetup")
    for item in setup:
        print(f"  {mark(item, first_setup)} {item.label}")

    items = []
    if not ready:
        print("\nTask\n  (checked once setup is done)")
    elif not task:
        if tasks:
            names = ", ".join(t.name for t in tasks)
            nxt = Next("you", f"There are several tasks ({names}). Switch to the branch of the one to work on:",
                       [f"git switch {BRANCH_PREFIX}<task-name>"])
        else:
            nxt = Next("together", "Help the student choose the hardest task in their field that a program can still "
                       "check. When they have picked one, and a short name like aurora-oval-boundary, create its "
                       "folder and branch:", [f"{HW} new <task-name>"], step="Step 1")
        items = [Item("branch", False, "choose the task; create its folder and branch", nxt)]
        items += [Item(k, None, label) for k, label in TASK_STEPS[1:]]
        print("\nTask: not chosen yet")
    else:
        items = task_items(c, task)
        print(f"\nTask: {rel(task)}")
    first_task = next((i for i in items if i.ok is False), None)
    for n, item in enumerate(items, 1):
        print(f"  {mark(item, first_task if not first_setup else None)} {n:>2}. {item.label}")

    print()
    if first_setup:
        first_setup.next.show()
    elif first_task:
        first_task.next.show()
    else:
        pr = c._pr or {}
        checks = {"passed": "GitHub's check passed: your reference solution scores 1 and doing nothing scores 0.",
                  "waiting": "GitHub's check (your reference solution must score 1, doing nothing 0) runs once the "
                             "instructor approves it, so \"awaiting approval\" is normal. Run this again later to see "
                             "the result."}.get(pr.get("checks"), "")
        Next("done", f"Week {WEEK_N} is submitted: {pr.get('url', '')}. {checks} From here the instructor runs "
             "frontier AI agents on every task.").show()
    if task:
        print(f'\nBefore ending a session: {HW} note "<where we are, what\'s next>"')
    return setup, items


# ---------------------------------------------------------------- commands

def current_task(c, arg=None):
    if arg:
        task = Path(arg).resolve()
        if not (task / "task.toml").is_file():
            sys.exit(f"{arg} is not a task folder (no task.toml).")
        return task
    for item in setup_items(c):
        if item.key in ("where", "gh", "login", "fork") and not item.ok:
            sys.exit(f"Setup isn't done. Run {HW} and follow its NEXT step.")
    task, _ = find_task(c)
    if not task:
        sys.exit(f"No task found for {c.login or 'you'}. Run {HW} to see what's next.")
    return task


def cmd_new(args):
    c = Ctx()
    require_setup(c)
    name = args.name
    if not SLUG.match(name):
        sys.exit("A task name is lowercase words joined by hyphens, e.g. aurora-oval-boundary.")
    task = ROOT / WEEK / "submissions" / c.login / name
    branch = BRANCH_PREFIX + name
    if task.exists():
        sys.exit(f"{rel(task)} already exists. To work on it: git switch {branch}")
    if c.branch != branch:
        if run(["git", "rev-parse", "--verify", "-q", "refs/heads/" + branch])[0] == 0:
            code, out, err = run(["git", "switch", branch])
        else:
            if c.class_remote:
                run(["git", "fetch", "-q", c.class_remote, "main"], timeout=60)
            code, out, err = run(["git", "switch", "-c", branch, c.base_ref()])
        if code != 0:
            sys.exit(f"Couldn't switch to branch {branch}:\n{err}")
        print(f"On branch {branch}.")
    email = git("config", "user.email")
    scaffold(task, c.login, git("config", "user.name") or c.login,
             email if email.endswith("@users.noreply.github.com") else "")
    print(f"Created {rel(task)} from the class templates.\n")
    status(Ctx())


def cmd_check(args):
    task = current_task(Ctx(), args.task)
    groups, warnings, check_task = lint(task)
    labels = {"layout": "folder layout", "files": "file sizes and secrets", "environment": "data and environment (Step 3a)",
              "instruction": "instruction (Step 3b)", "solution": "reference solution (Step 3c)",
              "tests": "verifier tests (Step 3d)", "window": "acceptance window, README Verification (Step 3e)",
              "metadata": "task.toml metadata (Step 3f)", "readme": "README (Step 3f)"}
    print(f"Static checks for {rel(task)}. CI runs the same ones.\n")
    count = 0
    for part in check_task.PARTS:
        if groups[part]:
            print(labels[part])
            for message, hint in groups[part]:
                count += 1
                print(f"  FAIL  {message}")
                for line in hint.splitlines():
                    print(f"        -> {line.strip()}")
    for message, hint in warnings:
        print(f"  WARN  {message}\n        -> {hint}")
    print(f"\n{count} to fix, in the order shown." if count else "All static checks passed.")
    sys.exit(1 if count else 0)


def cmd_note(args):
    task = current_task(Ctx())
    path = task / "authoring/attempts.md"
    text = read(path)
    body = f"## Status\n\n{args.text.strip()} ({today()})\n\n"
    if re.search(r"^## Status[ \t]*$", text, re.M):
        text = re.sub(r"^## Status[ \t]*\n.*?(?=^## |\Z)", lambda m: body, text, count=1, flags=re.M | re.S)
    else:
        text = text.rstrip("\n") + "\n\n" + body
    write(path, text.rstrip("\n") + "\n")
    print(f"Saved in {rel(path)}. The next session starts from it.")


def cmd_approve(args):
    what = args.what
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("This step is the student's: they approve by typing in their own terminal window"
              + (" (PowerShell or Windows Terminal)." if WINDOWS else "."))
        print(f"Ask them to run this, and wait until they say it's done:\n\n    {student_cmd(f'approve {what}')}\n")
        print("Never run it for them or feed it input.")
        sys.exit(2)
    c = Ctx()
    task = current_task(c)
    groups, _, _ = lint(task)
    blocking = {"instruction": ("instruction",), "window": ("tests", "window")}.get(what, ())
    problems = [p for name in blocking for p in groups[name]]
    if problems:
        print("Not ready to approve yet. Your agent still has to fix:")
        print("\n".join("  " + line for line in fix_list(problems)))
        sys.exit(1)
    rule = "-" * 72
    if what == "instruction":
        body = "\n".join(line for line in read(task / "instruction.md").splitlines() if "harbor-canary" not in line).strip()
        print(f"{rule}\nThe instruction the AI agent will get ({rel(task / 'instruction.md')}):\n{rule}\n{body}\n{rule}\n")
        points = ["You wrote it, or rewrote the agent's draft in your own words, and you stand behind every sentence.",
                  "An expert in your field could solve the task from this text and the data alone.",
                  "It doesn't give away the method or the answer, unless the method is part of the task."]
        record = fingerprint(task, "instruction.md")
    elif what == "window":
        verification = section(read(task / "README.md"), "## Verification") or ""
        print(f"{rule}\nWhy this acceptance window (README.md, Verification):\n{rule}\n{verification}\n")
        for test in sorted((task / "tests").glob("test_*.py")):
            code = "\n".join(line for line in read(test).splitlines() if "harbor-canary" not in line).strip()
            print(f"{rule}\nThe checks ({rel(test)}):\n{rule}\n{code}\n")
        print(rule + "\n")
        points = ["Answers from the good methods an expert might use land inside the window.",
                  "Wrong methods, and the textbook value, land outside it.",
                  "The tests check the result, not how it was computed."]
        record = window_fingerprint(task)
    else:
        items = [i for i in task_items(c, task, check_pr=False) if i.key not in ("publish", "pr")]
        missing = [i for i in items if not i.ok]
        if missing:
            print(f"Not ready to publish yet: \"{missing[0].label}\" isn't done. Your agent can see what's next with {HW}.")
            sys.exit(1)
        files = sorted(task_files(task) + [rel(task / PROGRESS)])
        total = sum((ROOT / f).stat().st_size for f in files if (ROOT / f).is_file())
        print(f"{rule}\nThese {len(files)} files ({total / 2**20:.1f} MB) will be public on GitHub:\n{rule}")
        for f in files:
            size = (ROOT / f).stat().st_size if (ROOT / f).is_file() else 0
            print(f"  {f}  ({size / 1024:.0f} KB)" if size >= 1024 else f"  {f}")
        print(rule + "\n")
        points = ["Everything listed becomes public on GitHub, permanently.",
                  "The data is yours to share, or openly licensed and its source is named in the README.",
                  "There are no passwords, API keys or tokens in these files.",
                  "You license this submission under the repository's MIT license."]
        record = fingerprint(task)
    print("Approve only if all of these are true:")
    for n, point in enumerate(points, 1):
        print(f"  {n}. {point}")
    try:
        answer = input('\nType "yes" to approve, or anything else to stop: ')
    except EOFError:
        answer = ""
    if answer.strip().lower() != "yes":
        print("Not approved. Tell your agent what to change.")
        sys.exit(1)
    progress = load_progress(task)
    progress[what] = {"approved": now(), "fingerprint": record}
    save_progress(task, progress)
    print("Approved and recorded. Go back to your agent and tell it it's done.")


def pr_body(c, task, ai):
    import tomllib
    config = tomllib.loads(read(task / "task.toml"))
    progress = load_progress(task)
    when = lambda key: (progress.get(key, {}).get("approved") or "")[:10]
    return f"""## Submission

- **Week:** {WEEK_N}
- **Folder:** `{rel(task)}`
- **In one sentence:** {config.get('task', {}).get('description', '').strip()}

## Checklist

- [x] Only files under `{WEEK}/submissions/{c.login}/` changed
- [x] No API keys, tokens or passwords anywhere
- [x] Any data is mine to share, or openly licensed (source named)
- [x] I agree to license this submission under this repository's MIT license
- [x] For a benchmark task: I wrote the instruction myself (or rewrote and approved every sentence)

## AI use

{ai.strip()}

<sub>Recorded by `tools/hw`: instruction approved {when('instruction')}, acceptance window approved {when('window')}, publishing approved {when('publish')}.</sub>
"""


def cmd_submit(args):
    c = Ctx()
    require_setup(c)
    task = current_task(c)
    items = task_items(c, task)
    missing = next((i for i in items if i.key != "pr" and not i.ok), None)
    if missing:
        print(f"Not ready to submit: \"{missing.label}\" isn't done.\n")
        missing.next.show()
        sys.exit(1)
    pr = c._pr
    if pr is False:
        sys.exit("Couldn't ask GitHub about pull requests. Check the internet connection and try again.")
    if pr and pr.get("state") == "MERGED":
        sys.exit(f"This task's pull request is already merged: {pr['url']}")
    if not pr and len((args.ai or "").strip()) < 10:
        print("Ask the student which AI agent(s) helped build the task, and how, in a sentence or two. Then run:\n")
        print(f'    {HW} submit --ai "<their answer>"')
        sys.exit(2)

    # A pull request may only change the student's own folder.
    if c.class_remote:
        run(["git", "fetch", "-q", c.class_remote, "main"], timeout=90)
    base = git("merge-base", "HEAD", c.base_ref()) or "HEAD"
    changed = git("diff", "--name-only", base, "HEAD").splitlines() + git("diff", "--cached", "--name-only").splitlines()
    mine = re.compile(rf"^week-[0-9]+/submissions/{re.escape(c.login)}/", re.I)
    outside = sorted(set(f for f in changed if f and not mine.match(f)))
    if outside:
        print(f"Only files under {WEEK}/submissions/{c.login}/ may change, but this branch also changes:")
        print("\n".join("    " + f for f in outside[:20]))
        print(f"\nUndo those changes on this branch (git restore --source {base[:12]} --staged --worktree <file>, "
              "then commit), and run this again.")
        sys.exit(1)

    branch = BRANCH_PREFIX + task.name
    title = f"[week {WEEK_N}] {task.name}"
    add = ["git", "add", "--", rel(task)]
    commit = ["git", "commit", "-q", "-m", ("Update " if pr else "Add ") + task.name]
    push = ["git", "push", "-u", "origin", branch]
    body_path = Path(tempfile.gettempdir()) / f"hw-pr-{task.name}.md"
    create = ["gh", "pr", "create", "--repo", CLASS_REPO, "--base", "main", "--head", f"{c.login}:{branch}",
              "--title", title, "--body-file", str(body_path)]
    if args.dry_run:
        print("Dry run. Would run:")
        for cmd in [add, commit, push] + ([] if pr else [create]):
            print("    " + " ".join(shlex.quote(part) for part in cmd))
        if not pr:
            print("\nwith this pull request description:\n")
            print(pr_body(c, task, args.ai))
        return
    code, out, err = run(add)
    if code != 0:
        sys.exit(f"git add failed:\n{err or out}")
    if run(["git", "diff", "--cached", "--quiet"])[0] != 0:
        code, out, err = run(commit)
        if code != 0:
            sys.exit(f"git commit failed:\n{err or out}")
        print(f"Committed: {commit[-1]}")
    code, out, err = run(push, timeout=180)
    if code != 0:
        sys.exit(f"git push failed:\n{err or out}")
    print(f"Pushed {branch} to your fork.")
    if pr:
        print(f"The pull request updates by itself: {pr['url']}")
    else:
        write(body_path, pr_body(c, task, args.ai))
        code, out, err = run(create, timeout=120)
        body_path.unlink()
        if code != 0:
            sys.exit(f"Opening the pull request failed:\n{err or out}")
        print(f"Opened the pull request: {out.splitlines()[-1] if out else ''}")
    print(f"\nNext: {HW}")


def main():
    if sys.version_info < (3, 11):
        sys.exit("Run this through uv, from the repository root: uv run tools/hw.py")
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    parser = argparse.ArgumentParser(prog=HW, description="The homework bookkeeper: where you are, and the one next step.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="the checklist and the next step (the default)")
    sub.add_parser("plan", help="what happens, start to finish: show it to the student first")
    p = sub.add_parser("new", help="create your task folder and its branch")
    p.add_argument("name", help="lowercase words joined by hyphens, e.g. aurora-oval-boundary")
    p = sub.add_parser("check", help="the static checks CI runs, grouped by step")
    p.add_argument("task", nargs="?", help="a task folder (default: yours)")
    p = sub.add_parser("approve", help="the student signs off, in their own terminal")
    p.add_argument("what", choices=["instruction", "window", "publish"])
    p = sub.add_parser("note", help="leave a note for the next session: where we are, what's next")
    p.add_argument("text")
    p = sub.add_parser("submit", help="commit, push and open (or update) the pull request")
    p.add_argument("--ai", help="which AI agent(s) helped build the task, and how")
    p.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing")
    args = parser.parse_args()
    commands = {"plan": cmd_plan, "new": cmd_new, "check": cmd_check, "approve": cmd_approve,
                "note": cmd_note, "submit": cmd_submit}
    if args.command in commands:
        commands[args.command](args)
    else:
        status()


if __name__ == "__main__":
    main()
