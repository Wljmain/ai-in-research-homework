"""CI helper: which task folders to validate, and whether a pull request stays in its author's folders
(week-<n>/submissions/<author>/ for any week).

Reads EVENT, BASE (a commit to diff against) and AUTHOR from the environment; writes
`tasks=<json list>` to $GITHUB_OUTPUT (or prints it).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MAINTAINERS = {"huangzesen"}
NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
TASK_DIR = re.compile(rf"^week-[0-9]+/submissions/[A-Za-z0-9-]+/{NAME}$")
TASK_WEEKS = {"week-1"}  # weeks whose submissions must be a benchmark task

event = os.environ.get("EVENT", "")
base = os.environ.get("BASE", "")
author_login = os.environ.get("AUTHOR", "")
author = author_login.lower()


def every_task():
    return sorted(str(p.parent) for p in Path(".").glob("week-*/submissions/*/*/task.toml"))


def changed_files():
    if not base or set(base) == {"0"}:
        return None
    diff = subprocess.run(["git", "diff", "--name-only", "-z", base, "HEAD"], capture_output=True, text=True)
    return [f for f in diff.stdout.split("\0") if f] if diff.returncode == 0 else None


changed = changed_files()

if event == "pull_request" and author not in MAINTAINERS and changed is not None:
    mine = re.compile(rf"^week-[0-9]+/submissions/{re.escape(author)}/")
    outside = [f for f in changed if not mine.match(f.lower())]
    if outside:
        print(f"::error::A pull request may only change files under week-<n>/submissions/{author_login}/. Also changed: {', '.join(outside[:10])}")
        sys.exit(1)

if changed is None or event == "workflow_dispatch" or any(f.startswith(("tools/", "templates/")) for f in changed):
    targets = every_task()
else:
    targets = set()
    for f in changed:
        parts = f.split("/")
        candidate = None
        if parts[0].startswith("week-") and len(parts) > 3 and parts[1] == "submissions":
            candidate = "/".join(parts[:4])
        if candidate and (Path(candidate) / "task.toml").is_file():
            targets.add(candidate)
    targets = sorted(targets)

if changed is not None:
    present = [f for f in changed if Path(f).exists()]
    misplaced = [f for f in present if Path(f).name == "task.toml" and str(Path(f).parent) not in targets]
    missing = event == "pull_request" and author not in MAINTAINERS and not targets and any(
        f.split("/")[0] in TASK_WEEKS for f in present)
    if misplaced or missing:
        print(f"::error::No valid task found. A task is a folder week-<n>/submissions/{author_login}/<task-name>/ "
              "with task.toml directly inside it. Create one in the right place with: uv run tools/hw.py new <task-name>")
        sys.exit(1)

bad = [t for t in targets if not TASK_DIR.match(t)]
if bad:
    print(f"::error::Task folders must be week-<n>/submissions/<github-username>/<lowercase-hyphenated-name>: {', '.join(bad)}")
    sys.exit(1)

line = f"tasks={json.dumps(targets)}"
print(line)
if os.environ.get("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(line + "\n")
