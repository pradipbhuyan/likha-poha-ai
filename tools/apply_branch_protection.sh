#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_TOKEN:?Set GITHUB_TOKEN to a repository-admin token}"

repo="pradipbhuyan/likha-poha-ai"
branch="main"

curl --fail-with-body --silent --show-error \
  --request PUT \
  --header "Accept: application/vnd.github+json" \
  --header "Authorization: Bearer ${GITHUB_TOKEN}" \
  --header "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${repo}/branches/${branch}/protection" \
  --data @- <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI Passed"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_linear_history": false,
  "lock_branch": false,
  "allow_fork_syncing": true
}
JSON

echo "Branch protection applied to ${repo}:${branch}."
