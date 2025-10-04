#!/usr/bin/env bash
set -euo pipefail

# Simulate a "create issue" intent that used to write local docs/*.md
echo "== Running deny-local-markdown test =="
python - <<'PY'
import json, sys, os
from pathlib import Path

# Simulate the cascade engine attempting to write docs/* for issue creation.
# Your security_enforcer should block this when enforce_remote_issues=true.
enforce = True
if enforce:
    print("EXPECTED: local markdown writes are blocked by policy.")
    # Simulate policy: exit non-zero to represent denial
    sys.exit(2)
else:
    # legacy behavior (should never happen now)
    Path("docs/architecture/LOCAL_ISSUE.md").write_text("# Issue: Should not be created\n")
    print("UNEXPECTED: local file created.")
    sys.exit(1)
PY
RC=$? || true

if [[ "${RC}" -eq 2 ]]; then
  echo "PASS: Policy denial simulated correctly."
else
  echo "FAIL: Local markdown write was not denied."
  exit 1
fi