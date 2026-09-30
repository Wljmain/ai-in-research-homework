"""Static checks for a class task: layout, task.toml, instruction, verifier isolation, size, secrets.

Fast (no Docker). Run it through tools/validate.sh, or directly:
    uv run --python 3.12 tools/check_task.py tasks/<github-username>/<task-name>
Exit code 1 if any check fails. Warnings don't fail.
"""
import re
import sys
import tomllib
from pathlib import Path

REPO = "ai-in-research-homework"
DOMAINS = {"life-sciences", "physical-sciences", "earth-sciences", "mathematical-sciences", "engineering-sciences"}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SUFFIX = "You have {n} seconds to complete this task. Do not cheat by using online solutions or hints specific to this task."
SECRETS = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{10,}|sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
MAX_FILE_MB, MAX_TOTAL_MB = 20, 50

failures, warnings = [], []


def fail(message, hint):
    failures.append((message, hint))


def warn(message, hint):
    warnings.append((message, hint))


def read(path):
    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError):
        return ""


def check(task):
    parts = task.resolve().parts
    name = task.resolve().name
    owner = None
    if "tasks" in parts and parts.index("tasks") == len(parts) - 3:
        owner = parts[-2]
    elif not ("examples" in parts and parts.index("examples") == len(parts) - 2):
        fail("the task is not at tasks/<github-username>/<task-name>/", "Move it there; CI only accepts that layout.")
    if not SLUG.match(name):
        fail(f"task folder name '{name}' is not lowercase-with-hyphens", "Rename it, e.g. solar-wind-spectral-index.")

    required = [
        "task.toml", "instruction.md", "README.md", "environment/Dockerfile", "solution/solve.sh",
        "tests/Dockerfile", "tests/test.sh", "authoring/attempts.md",
    ]
    for rel in required:
        if not (task / rel).is_file():
            fail(f"missing {rel}", "tools/new_task.sh creates every required file; copy the missing one from templates/ or examples/.")
    if not list((task / "tests").glob("test_*.py")):
        fail("no tests/test_*.py", "The verifier's checks live in pytest files named test_*.py.")
    if failures:
        return  # the rest assumes the layout exists

    # --- task.toml
    try:
        config = tomllib.loads(read(task / "task.toml"))
    except tomllib.TOMLDecodeError as e:
        fail(f"task.toml is not valid TOML: {e}", "Fix the syntax; a missing quote or bracket is the usual cause.")
        return
    info, meta = config.get("task", {}), config.get("metadata", {})
    if info.get("name") != f"{REPO}/{name}":
        fail(f"[task] name is {info.get('name')!r}", f'Set name = "{REPO}/{name}" (it must match the folder).')
    if not str(info.get("description", "")).strip():
        fail("[task] description is empty", "One sentence saying what the task asks for.")
    if not info.get("authors"):
        fail("no [[task.authors]]", 'Add [[task.authors]] with name = "Your Name".')
    for key in ("author_name", "field", "relevant_experience"):
        if not str(meta.get(key, "")).strip():
            fail(f"[metadata] {key} is empty", "Fill in every [metadata] field.")
    if meta.get("domain") not in DOMAINS:
        fail(f"[metadata] domain is {meta.get('domain')!r}", "Use one of: " + ", ".join(sorted(DOMAINS)) + ".")
    if owner and str(meta.get("github_username", "")).lower() != owner.lower():
        fail(f"[metadata] github_username is {meta.get('github_username')!r}, folder owner is '{owner}'",
             "Set github_username to your GitHub username, the same as your folder under tasks/.")

    verifier = config.get("verifier", {})
    if verifier.get("environment_mode") != "separate":
        fail("the verifier does not run in its own container", 'Set environment_mode = "separate" under [verifier].')
    if verifier.get("environment", {}).get("network_mode") != "no-network":
        fail("the verifier can reach the network", 'Add [verifier.environment] with network_mode = "no-network".')

    timeout = config.get("agent", {}).get("timeout_sec")
    if not isinstance(timeout, (int, float)) or not 60 <= timeout <= 3600:
        fail(f"[agent] timeout_sec is {timeout!r}", "Use 60 to 3600 seconds for class tasks (most need 600-1800).")
    env = config.get("environment", {})
    if env.get("gpus", 0) != 0:
        fail("the task asks for a GPU", "CI runners have no GPU; set gpus = 0.")
    if env.get("cpus", 1) > 4 or env.get("memory_mb", 2048) > 8192:
        fail("the task asks for more than 4 CPUs or 8 GB of memory", "CI runners have 4 CPUs and 16 GB; stay within 4 CPUs / 8192 MB.")

    artifacts = config.get("artifacts", [])
    paths = [a if isinstance(a, str) else a.get("source", "") for a in artifacts]
    if not paths:
        fail("artifacts is empty", 'List the output files the verifier grades, e.g. artifacts = ["/root/results/answer.json"].')
    instruction = read(task / "instruction.md")
    tests_dockerfile = read(task / "tests/Dockerfile")
    for path in paths:
        if not path.startswith("/"):
            fail(f"artifact {path!r} is not an absolute path", "Use absolute container paths like /root/results/out.csv.")
            continue
        if path not in instruction:
            fail(f"instruction.md never mentions the artifact {path}", "Tell the agent exactly where to write each output.")
        parent = path.rsplit("/", 1)[0] or "/"
        if parent != "/" and parent not in tests_dockerfile:
            fail(f"tests/Dockerfile doesn't create {parent}", f"Add: RUN mkdir -p {parent}")

    # --- instruction
    lines = [line.strip() for line in instruction.splitlines() if line.strip() and not line.strip().startswith("<!--")]
    if isinstance(timeout, (int, float)):
        expected = SUFFIX.format(n=int(timeout))
        if not lines or lines[-1] != expected:
            fail("instruction.md doesn't end with the required last line", f"End it with exactly:\n        {expected}")
    if len(lines) < 2:
        fail("instruction.md is (nearly) empty", "Describe the inputs, what to compute and the output format.")

    # --- verifier and environment
    if "COPY . /tests" not in tests_dockerfile:
        fail("tests/Dockerfile doesn't copy the tests in", "Add: COPY . /tests/")
    test_sh = read(task / "tests/test.sh")
    if "/logs/verifier/reward" not in test_sh:
        fail("tests/test.sh never writes /logs/verifier/reward.txt", "Copy templates/tests/test.sh.")
    if re.search(r"\b(pip|pip3|uv|uvx|apt-get|apt|curl|wget)\b", test_sh):
        fail("tests/test.sh installs or downloads something", "The verifier has no network: install in tests/Dockerfile instead.")
    env_dockerfile = read(task / "environment/Dockerfile")
    if re.search(r"^\s*(COPY|ADD)\b.*\b(solution|tests)\b", env_dockerfile, re.M | re.I):
        fail("environment/Dockerfile copies solution or test files", "The agent's container must not contain answers or tests.")

    # --- leftovers from the scaffold
    for rel in ("instruction.md", "solution/solve.sh", "environment/Dockerfile", "README.md"):
        text = read(task / rel)
        if "Use this file to" in text or "Install or copy over any environment dependencies here" in text or "Task title" in text:
            fail(f"{rel} still has scaffold placeholder text", "Replace the template text with your own.")
    if "Use this file to define pytest tests" in "".join(read(p) for p in (task / "tests").glob("test_*.py")):
        fail("tests still have the scaffold placeholder", "Write real checks; a test that only says `pass` grades nothing.")

    # --- README
    readme = read(task / "README.md")
    for section in ("## Difficulty", "## Reference solution", "## Verification"):
        match = re.search(re.escape(section) + r"\s*\n(.*?)(?=\n## |\Z)", readme, re.S)
        if not match or len(re.sub(r"<!--.*?-->", "", match.group(1), flags=re.S).strip()) < 40:
            fail(f"README.md section '{section}' is missing or too short", "A few real sentences each; see examples/.")

    # --- size and secrets
    total = 0
    for path in task.rglob("*"):
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        if size > MAX_FILE_MB * 2**20:
            fail(f"{path.relative_to(task)} is {size / 2**20:.0f} MB", f"Keep files under {MAX_FILE_MB} MB: subsample, compress, or generate the data at build time.")
        if size < 2**20 and SECRETS.search(read(path)):
            fail(f"{path.relative_to(task)} seems to contain an API key or token",
                 "Remove it now, and revoke it with the provider: anything pushed to GitHub is public.")
    if total > MAX_TOTAL_MB * 2**20:
        fail(f"the task is {total / 2**20:.0f} MB in total", f"Keep the whole task under {MAX_TOTAL_MB} MB.")
    elif total > 10 * 2**20:
        warn(f"the task is {total / 2**20:.0f} MB", "Smaller data makes the repo faster for everyone; can you subsample?")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: check_task.py tasks/<github-username>/<task-name>")
    task = Path(sys.argv[1])
    if not task.is_dir():
        sys.exit(f"{task} is not a folder")
    check(task)
    for message, hint in failures:
        print(f"FAIL  {message}\n      -> {hint}")
    for message, hint in warnings:
        print(f"WARN  {message}\n      -> {hint}")
    print(f"\n{len(failures)} failed, {len(warnings)} warnings" if failures or warnings else "All static checks passed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
