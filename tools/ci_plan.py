"""CI helper: which task folders to validate, and whether a pull request stays in its author's folder.

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
TASK_DIR = re.compile(r"^(tasks/[A-Za-z0-9-]+/[a-z0-9]+(?:-[a-z0-9]+)*|examples/[a-z0-9]+(?:-[a-z0-9]+)*)$")

event = os.environ.get("EVENT", "")
base = os.environ.get("BASE", "")
author_login = os.environ.get("AUTHOR", "")
author = author_login.lower()


def every_task():
    found = [p.parent for p in Path("examples").glob("*/task.toml")] + [p.parent for p in Path("tasks").glob("*/*/task.toml")]
    return sorted(str(p) for p in found)


def changed_files():
    if not base or set(base) == {"0"}:
        return None
    diff = subprocess.run(["git", "diff", "--name-only", "-z", base, "HEAD"], capture_output=True, text=True)
    return [f for f in diff.stdout.split("\0") if f] if diff.returncode == 0 else None


changed = changed_files()

if event == "pull_request" and author not in MAINTAINERS and changed is not None:
    outside = [f for f in changed if not f.lower().startswith(f"tasks/{author}/")]
    if outside:
        print(f"::error::A pull request may only change files under tasks/{author_login}/. Also changed: {', '.join(outside[:10])}")
        sys.exit(1)

if changed is None or event == "workflow_dispatch" or any(f.startswith(("tools/", "templates/")) for f in changed):
    targets = every_task()
else:
    targets = set()
    for f in changed:
        parts = f.split("/")
        candidate = "/".join(parts[:3]) if parts[0] == "tasks" else "/".join(parts[:2]) if parts[0] == "examples" else None
        if candidate and (Path(candidate) / "task.toml").is_file():
            targets.add(candidate)
    targets = sorted(targets)

if event == "pull_request" and author not in MAINTAINERS and changed and not targets:
    added = [f for f in changed if Path(f).exists()]
    if added:
        print(f"::error::No task found. A task folder must be tasks/{author_login}/<task-name>/ with a task.toml directly inside it. "
              "Run tools/new_task.sh to create one in the right place.")
        sys.exit(1)

bad = [t for t in targets if not TASK_DIR.match(t)]
if bad:
    print(f"::error::Task folders must be tasks/<github-username>/<lowercase-hyphenated-name>: {', '.join(bad)}")
    sys.exit(1)

line = f"tasks={json.dumps(targets)}"
print(line)
if os.environ.get("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(line + "\n")
