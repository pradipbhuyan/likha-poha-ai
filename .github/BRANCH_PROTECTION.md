# Main branch protection

Apply the repository policy with an administrator token:

```bash
GITHUB_TOKEN=... bash tools/apply_branch_protection.sh
```

The policy requires one approved pull request, an up-to-date `CI Passed`
check, resolved conversations, and applies to administrators. Direct pushes,
force pushes, and branch deletion are blocked.

After applying it, verify in GitHub under **Settings → Branches → main** and
confirm that repository administrators cannot bypass the rule.
