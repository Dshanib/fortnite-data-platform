#!/usr/bin/env bash
# Apply dev-branch ruleset on GitHub (requires gh or curl + GITHUB_TOKEN with repo admin).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OWNER="${GITHUB_OWNER:-Dshanib}"
REPO="${GITHUB_REPO:-fortnite-data-platform}"
RULESET_FILE=".github/rulesets/dev-restricted-push.json"

if command -v gh >/dev/null 2>&1; then
  gh api --method POST \
    -H "Accept: application/vnd.github+json" \
    "/repos/${OWNER}/${REPO}/rulesets" \
    --input "$RULESET_FILE" \
    || gh api --method PUT \
      -H "Accept: application/vnd.github+json" \
      "/repos/${OWNER}/${REPO}/rulesets/$(gh api "/repos/${OWNER}/${REPO}/rulesets" --jq '.[] | select(.name==\"dev-restricted-push\") | .id')" \
      --input "$RULESET_FILE"
  echo "Ruleset applied on ${OWNER}/${REPO} (see Settings → Rules → Rulesets)."
  exit 0
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Install GitHub CLI (gh) or set GITHUB_TOKEN, then re-run." >&2
  echo "Manual UI: Settings → Rules → Rulesets → import ${RULESET_FILE}" >&2
  exit 1
fi

curl -fsSL -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/${OWNER}/${REPO}/rulesets" \
  --data-binary "@${RULESET_FILE}"
echo "Ruleset created. Update via PUT if it already exists."
