#!/usr/bin/env bash
# Scaffolds a class task: Harbor's layout, the class task.toml defaults, a separate offline
# verifier, the README sections and the attempts log.
# Usage: tools/new_task.sh <github-username> <task-name> "Your Name" [email]
set -euo pipefail
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
dir="$root/tasks/$user/$name"
if [ -e "$dir" ]; then
  echo "$dir already exists." >&2
  exit 1
fi

mkdir -p "$root/tasks/$user"
uvx "harbor@$HARBOR_VERSION" task init "ai-in-research-homework/$name" -p "$root/tasks/$user" \
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

echo "Created tasks/$user/$name"
if [ -n "$email" ]; then echo "Note: $email is now in task.toml, which becomes public when you open a pull request."; fi
echo "Next: write instruction.md, environment/, solution/ and tests/, then run: tools/validate.sh tasks/$user/$name"
