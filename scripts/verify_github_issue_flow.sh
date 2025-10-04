#!/usr/bin/env bash
set -euo pipefail

REPO_JSON=".windsurf/github-repo.json"
DEFAULT_REPO="$(jq -r '.default_repo' "${REPO_JSON}")"

echo "== Checking gh auth =="
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh not authenticated. Run: gh auth login"
  exit 1
fi

if [[ -z "${DEFAULT_REPO}" || "${DEFAULT_REPO}" == "null" ]]; then
  echo "ERROR: default_repo not set in ${REPO_JSON}"
  exit 1
fi

echo "== Ensuring labels =="
gh label create dx --repo "${DEFAULT_REPO}" --color "0e8a16" --description "Developer Experience" 2>/dev/null || true

TITLE="DX flow check $(date -u +%Y-%m-%dT%H:%M:%SZ)"
BODY="Automated validation of GitHub-first issue flow."
echo "== Creating issue =="
URL=$(gh issue create --repo "${DEFAULT_REPO}" --title "${TITLE}" --body "${BODY}" --label dx | tail -1)
NUM="${URL##*/}"
echo "Created: ${URL}"

echo "== Commenting and closing =="
gh issue comment "${NUM}" --repo "${DEFAULT_REPO}" --body "Automated comment from validation script."
gh issue close "${NUM}" --repo "${DEFAULT_REPO}" --reason "completed"

echo "PASS: GitHub flow validated."