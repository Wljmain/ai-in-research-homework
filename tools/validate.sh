#!/usr/bin/env bash
# Is this task valid? Static checks, then the reference solution must score 1 and an agent that
# does nothing must score 0. CI runs exactly this on every pull request.
# Usage: tools/validate.sh tasks/<github-username>/<task-name>
set -uo pipefail
HARBOR_VERSION=0.23.0
task="${1:?usage: tools/validate.sh tasks/<github-username>/<task-name>}"
task="${task%/}"
root="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Static checks"
uv run -q --python 3.12 "$root/tools/check_task.py" "$task" || exit 1

jobs="$root/jobs/validate/$(basename "$task")-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$jobs"
status=0
for pair in oracle:1 nop:0; do
  agent="${pair%:*}"
  want="${pair#*:}"
  echo
  echo "== $agent agent: expect reward $want (the first Docker build can take a few minutes)"
  uvx "harbor@$HARBOR_VERSION" run -p "$task" -a "$agent" -o "$jobs" --job-name "$agent" -y > "$jobs/$agent.log" 2>&1
  got="$(uv run -q --python 3.12 "$root/tools/reward.py" "$jobs/$agent")"
  if [ "$(printf '%s' "$got" | cut -d. -f1)" = "$want" ]; then
    echo "PASS  $agent scored $got"
  else
    status=1
    echo "FAIL  $agent scored: $got"
    out="$(ls "$jobs/$agent"/*/verifier/test-stdout.txt 2>/dev/null | head -1)"
    if [ -n "$out" ]; then
      echo "      Verifier output (last lines of $out):"
      tail -n 25 "$out" | sed 's/^/      | /'
    else
      echo "      Full log: $jobs/$agent.log"
    fi
  fi
done

echo
if [ "$status" -eq 0 ]; then
  echo "Task is valid: the reference solution passes and doing nothing fails."
else
  echo "Not valid yet. Job folders are in $jobs"
fi
exit "$status"
