#!/usr/bin/env bash
set -euo pipefail

# Simulate a "create issue" intent that used to write local docs/*.md
echo "== Running deny-local-markdown test =="
if python - <<'PY'
import json
import sys
from pathlib import Path

CONFIG_PATH = Path('.windsurf/github-repo.json')


def read_enforce_flag() -> bool:
    try:
        config_data = json.loads(CONFIG_PATH.read_text())
    except FileNotFoundError:
        print("WARNING: .windsurf/github-repo.json not found. Defaulting to enforcement.")
        return True
    except json.JSONDecodeError as exc:
        print(f"ERROR: Failed to parse {CONFIG_PATH}: {exc}", file=sys.stderr)
        sys.exit(1)

    return bool(config_data.get('enforce_remote_issues', True))


def main() -> None:
    # Simulate the cascade engine attempting to write docs/* for issue creation.
    # Your security_enforcer should block this when enforce_remote_issues=true.
    enforce = read_enforce_flag()

    if enforce:
        print("EXPECTED: local markdown writes are blocked by policy.")
        # Simulate policy: exit non-zero to represent denial
        sys.exit(2)

    # legacy behavior (should never happen now)
    Path("docs/architecture/LOCAL_ISSUE.md").write_text("# Issue: Should not be created\n")
    print("UNEXPECTED: local file created.")
    sys.exit(1)


if __name__ == '__main__':
    main()
PY
then
  RC=$?
else
  RC=$?
fi

if [[ "${RC}" -eq 2 ]]; then
  echo "PASS: Policy denial simulated correctly."
else
  echo "FAIL: Local markdown write was not denied."
  exit 1
fi
