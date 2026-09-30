"""Static checks for a class task: layout, task.toml, instruction, verifier isolation, size, secrets.

Fast (no Docker). Run it through `uv run tools/hw.py check` or tools/validate.sh, or directly:
    uv run --python 3.12 tools/check_task.py week-1/submissions/<github-username>/<task-name>
Exit code 1 if any check fails. Warnings don't fail. Each failure names the part of the task it
belongs to (PARTS, in the order a task is built), so tools/hw.py can say which step to fix.
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
    r"|eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}|\"refresh_token\"\s*:"
)
SECRET_FILES = re.compile(r"^(auth\.json|\.env(\..*)?|.*\.pem|.*\.key|credentials(\.json)?)$")
SKIP_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", ".git"}
MAX_FILE_MB, MAX_TOTAL_MB = 20, 50
TEMPLATE_README = Path(__file__).resolve().parent.parent / "templates" / "README.md"
PARTS = ("layout", "files", "environment", "instruction", "solution", "tests", "window", "metadata", "readme")
README_SECTIONS = {"## Difficulty": "readme", "## Reference solution": "readme", "## Verification": "window"}

failures, warnings = [], []


def fail(part, message, hint):
    failures.append((part, message, hint))


def warn(part, message, hint):
    warnings.append((part, message, hint))


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def section(text, heading):
    """The body of a `## heading` section without HTML comments, or None if there is no such section."""
    match = re.search(re.escape(heading) + r"[ \t]*\n(.*?)(?=\n## |\Z)", text, re.S)
    return re.sub(r"<!--.*?-->", "", match.group(1), flags=re.S).strip() if match else None


def check(task):
    parts = task.resolve().parts
    name = task.resolve().name
    owner = None
    if len(parts) >= 4 and parts[-3] == "submissions" and parts[-4].startswith("week-"):
        owner = parts[-2]
    else:
        fail("layout", "the task is not at week-<n>/submissions/<github-username>/<task-name>/", "Move it there; CI only accepts that layout.")
    if not SLUG.match(name):
        fail("layout", f"task folder name '{name}' is not lowercase-with-hyphens", "Rename it: lowercase words joined by hyphens.")

    required = [
        "task.toml", "instruction.md", "README.md", "environment/Dockerfile", "solution/solve.sh",
        "tests/Dockerfile", "tests/test.sh", "authoring/attempts.md",
    ]
    for rel in required:
        if not (task / rel).is_file():
            fail("layout", f"missing {rel}", "`uv run tools/hw.py new` creates every required file; copy the missing one from templates/.")
    if not list((task / "tests").glob("test_*.py")):
        fail("layout", "no tests/test_*.py", "The verifier's checks live in pytest files named test_*.py.")
    if failures:
        return  # the rest assumes the layout exists

    # --- task.toml
    try:
        config = tomllib.loads(read(task / "task.toml"))
    except tomllib.TOMLDecodeError as e:
        fail("metadata", f"task.toml is not valid TOML: {e}", "Fix the syntax; a missing quote or bracket is the usual cause.")
        return
    info, meta = config.get("task", {}), config.get("metadata", {})
    if info.get("name") != f"{REPO}/{name}":
        fail("metadata", f"[task] name is {info.get('name')!r}", f'Set name = "{REPO}/{name}" (it must match the folder).')
    if not str(info.get("description", "")).strip():
        fail("metadata", "[task] description is empty", "One sentence saying what the task asks for.")
    authors = info.get("authors") or []
    if not authors or not all(str(a.get("name", "")).strip() for a in authors if isinstance(a, dict)):
        fail("metadata", "[[task.authors]] has no name", 'Set name = "Your Name" under [[task.authors]].')
    for key in ("author_name", "field", "relevant_experience"):
        if not str(meta.get(key, "")).strip():
            fail("metadata", f'[metadata] {key} = "" needs a value', "Fill in every [metadata] field; the comments in task.toml give examples.")
    hours = meta.get("expert_time_estimate_hours", 0)
    if not isinstance(hours, (int, float)) or hours <= 0:
        fail("metadata", "[metadata] expert_time_estimate_hours is not set", "Estimate how many hours a focused top expert needs, e.g. 6.0.")
    if meta.get("domain") not in DOMAINS:
        fail("metadata", f"[metadata] domain is {meta.get('domain')!r}", "Use one of: " + ", ".join(sorted(DOMAINS)) + ".")
    if owner and str(meta.get("github_username", "")).lower() != owner.lower():
        fail("metadata", f"[metadata] github_username is {meta.get('github_username')!r}, folder owner is '{owner}'",
             "Set github_username to your GitHub username, the same as your folder under submissions/.")

    verifier = config.get("verifier", {})
    if verifier.get("environment_mode") != "separate":
        fail("tests", "the verifier does not run in its own container", 'Set environment_mode = "separate" under [verifier].')
    if verifier.get("environment", {}).get("network_mode") != "no-network":
        fail("tests", "the verifier can reach the network", 'Add [verifier.environment] with network_mode = "no-network".')

    timeout = config.get("agent", {}).get("timeout_sec")
    if not isinstance(timeout, (int, float)) or not 300 <= timeout <= 18000:
        fail("instruction", f"[agent] timeout_sec is {timeout!r}", "Use 300 to 18000 seconds (5 hours): the time a strong expert needs, with margin.")
    env = config.get("environment", {})
    if env.get("gpus", 0) != 0:
        fail("environment", "the task asks for a GPU", "CI runners have no GPU; set gpus = 0.")
    if env.get("cpus", 1) > 4 or env.get("memory_mb", 2048) > 8192:
        fail("environment", "the task asks for more than 4 CPUs or 8 GB of memory", "CI runners have 4 CPUs and 16 GB; stay within 4 CPUs / 8192 MB.")

    artifacts = config.get("artifacts", [])
    paths = [a if isinstance(a, str) else a.get("source", "") for a in artifacts]
    if not paths:
        fail("instruction", "artifacts in task.toml is empty",
             'List the output files the instruction asks for, e.g. artifacts = ["/root/results/answer.json"].')
    instruction = read(task / "instruction.md")
    tests_dockerfile = read(task / "tests/Dockerfile")
    for path in paths:
        if not path.startswith("/"):
            fail("instruction", f"artifact {path!r} is not an absolute path", "Use absolute container paths like /root/results/out.csv.")
            continue
        if path not in instruction:
            fail("instruction", f"instruction.md never mentions the artifact {path}", "Tell the agent exactly where to write each output.")
        parent = path.rsplit("/", 1)[0] or "/"
        if parent != "/" and parent not in tests_dockerfile:
            fail("tests", f"tests/Dockerfile doesn't create {parent}", f"Add: RUN mkdir -p {parent}")

    # --- instruction
    lines = [line.strip() for line in instruction.splitlines() if line.strip() and not line.strip().startswith("<!--")]
    if isinstance(timeout, (int, float)):
        expected = SUFFIX.format(n=int(timeout))
        if not lines or lines[-1] != expected:
            fail("instruction", "instruction.md doesn't end with the required last line", f"End it with exactly:\n        {expected}")
    if len(lines) < 2:
        fail("instruction", "instruction.md is (nearly) empty", "Describe the inputs, what to compute and the output format.")

    # --- verifier and environment
    if "COPY . /tests" not in tests_dockerfile:
        fail("tests", "tests/Dockerfile doesn't copy the tests in", "Add: COPY . /tests/")
    test_sh = read(task / "tests/test.sh")
    if "/logs/verifier/reward" not in test_sh:
        fail("tests", "tests/test.sh never writes /logs/verifier/reward.txt", "Copy templates/tests/test.sh.")
    if re.search(r"\b(pip|pip3|uv|uvx|apt-get|apt|curl|wget)\b", test_sh):
        fail("tests", "tests/test.sh installs or downloads something", "The verifier has no network: install in tests/Dockerfile instead.")
    env_dockerfile = read(task / "environment/Dockerfile")
    if re.search(r"^\s*(COPY|ADD)\b.*\b(solution|tests)\b", env_dockerfile, re.M | re.I):
        fail("environment", "environment/Dockerfile copies solution or test files", "The agent's container must not contain answers or tests.")

    # --- leftovers from the scaffold
    for rel, part in (("environment/Dockerfile", "environment"), ("instruction.md", "instruction"),
                      ("solution/solve.sh", "solution"), ("README.md", "readme")):
        text = read(task / rel)
        if any(marker in text for marker in ("Use this file to", "Install or copy over any environment dependencies here",
                                              "Task title", "Your Name (UCLA)", "One or two sentences: what the solver")):
            fail(part, f"{rel} still has scaffold placeholder text", "Replace the template text with your own.")
    if "Use this file to define pytest tests" in "".join(read(p) for p in (task / "tests").glob("test_*.py")):
        fail("tests", "tests still have the scaffold placeholder", "Write real checks; a test that only says `pass` grades nothing.")

    # --- README: three sections of real prose, not the template's prompts
    readme, template = read(task / "README.md"), read(TEMPLATE_README)
    for heading, part in README_SECTIONS.items():
        body, prompt = section(readme, heading), section(template, heading)
        if not body or len(body) < 40:
            fail(part, f"README.md section '{heading}' is missing or too short", "A few real sentences each.")
        elif prompt and prompt.split("\n")[0][:40] in body:
            fail(part, f"README.md section '{heading}' still has the template's prompt", "Replace it with your own sentences.")

    # --- size and secrets
    total = 0
    for path in task.rglob("*"):
        if not path.is_file() or SKIP_DIRS.intersection(path.relative_to(task).parts):
            continue
        if SECRET_FILES.match(path.name):
            fail("files", f"{path.relative_to(task)} looks like a credentials file", "Delete it from the task; credentials never go in git.")
        size = path.stat().st_size
        total += size
        if size > MAX_FILE_MB * 2**20:
            fail("files", f"{path.relative_to(task)} is {size / 2**20:.0f} MB", f"Keep files under {MAX_FILE_MB} MB: subsample, compress, or generate the data at build time.")
        if size < 2**20 and SECRETS.search(read(path)):
            fail("files", f"{path.relative_to(task)} seems to contain an API key or token",
                 "Remove it now, and revoke it with the provider: anything pushed to GitHub is public.")
    if total > MAX_TOTAL_MB * 2**20:
        fail("files", f"the task is {total / 2**20:.0f} MB in total", f"Keep the whole task under {MAX_TOTAL_MB} MB.")
    elif total > 10 * 2**20:
        warn("files", f"the task is {total / 2**20:.0f} MB", "Smaller data makes the repo faster for everyone; can you subsample?")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: check_task.py week-1/submissions/<github-username>/<task-name>")
    task = Path(sys.argv[1])
    if not task.is_dir():
        sys.exit(f"{task} is not a folder")
    check(task)
    for _, message, hint in failures:
        print(f"FAIL  {message}\n      -> {hint}")
    for _, message, hint in warnings:
        print(f"WARN  {message}\n      -> {hint}")
    print(f"\n{len(failures)} failed, {len(warnings)} warnings" if failures or warnings else "All static checks passed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
