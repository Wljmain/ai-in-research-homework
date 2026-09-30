#!/usr/bin/env bash
# Scaffolds a class task: Harbor's layout, the class task.toml defaults, a separate offline
# verifier, the README sections and the attempts log.
# Usage: tools/new_task.sh <github-username> <task-name> "Your Name" [email]   (tools/hw new runs this for you)
# Creates week-1/submissions/<github-username>/<task-name>/ (set WEEK=week-N for another week).
set -euo pipefail
WEEK="${WEEK:-week-1}"
HARBOR_VERSION=0.23.0
usage='usage: tools/new_task.sh <github-username> <task-name> "Your Name" [email]'
user="${1:?$usage}"
name="${2:?$usage}"
author="${3:?$usage}"
email="${4:-}"
root="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! "$user" =~ ^[A-Za-z0-9-]+$ ]]; then
  echo "GitHub username should be letters, digits and hyphens only; check it with: gh api user --jq .login" >&2
  exit 1
fi
if [[ ! "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "Task name must be lowercase words joined by hyphens, e.g. exoplanet-transit-depth." >&2
  exit 1
fi
base="$root/$WEEK/submissions/$user"
dir="$base/$name"
if [ -e "$dir" ]; then
  echo "$dir already exists." >&2
  exit 1
fi

mkdir -p "$base"
uvx "harbor@$HARBOR_VERSION" task init "ai-in-research-homework/$name" -p "$base" \
  --include-canary-strings --metadata-template "$root/templates/task.toml" \
  --author "$author${email:+ <$email>}" >/dev/null

# The verifier runs in its own container with no network: its own Dockerfile, an offline test.sh.
cp "$root/templates/tests/Dockerfile" "$root/templates/tests/test.sh" "$dir/tests/"
cp "$root/templates/README.md" "$dir/README.md"
mkdir -p "$dir/authoring/provenance" "$dir/authoring/evidence"
cp "$root/templates/attempts.md" "$dir/authoring/attempts.md"

# Fill in the metadata we already know.
uv run -q --python 3.12 python - "$dir/task.toml" "$author" "$email" "$user" <<'PY'
import json, re, sys
path, author, email, user = sys.argv[1:]
text = open(path).read()
for key, value in (("author_name", author), ("author_email", email), ("github_username", user)):
    text = re.sub(rf'^{key} = ""', f"{key} = {json.dumps(value)}", text, count=1, flags=re.M)
open(path, "w").write(text)
PY

echo "Created $WEEK/submissions/$user/$name"
if [ -n "$email" ]; then echo "Note: $email is now in task.toml, which becomes public when you open a pull request."; fi
echo "Next: run tools/hw to see the next step."
