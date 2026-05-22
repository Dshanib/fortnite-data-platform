# `dev` branch access control

## Who can push directly to `dev`

| Actor | GitHub login | Notes |
|-------|----------------|-------|
| You (repo owner) | `Dshanib` | Always allowed (admin) |
| Mayanhad | `maayanhad` | Must **accept** the repo collaborator invite sent to `Mayanhad@gmail.com` |
| Cursor / AI agents | — | **Cannot** be added on GitHub (not a GitHub user) |

Everyone else must open a **pull request** into `dev` (at least one approval) and cannot force-push or delete the branch.

## How it is enforced

Repository ruleset **`dev-restricted-push`** (Settings → Rules → Rulesets):

- Applies to `refs/heads/dev`
- Requires a pull request + 1 approval for users **not** on the bypass list
- Bypass list: `Dshanib`, `maayanhad`
- Blocks force-push and branch deletion

Config lives in [`.github/rulesets/dev-restricted-push.json`](../.github/rulesets/dev-restricted-push.json).

Re-apply after cloning:

```bash
bash scripts/setup_dev_branch_protection.sh
```

## Personal repo limitation

GitHub’s **“Restrict who can push”** checkbox only works for **organization** repositories. This project uses a **ruleset + bypass list** instead, which works on `Dshanib/fortnite-data-platform`.

For hard “only these logins may push” on a personal repo, transfer the repo to a GitHub Organization and use branch restrictions there.

## Add or change people

1. Invite them: **Settings → Collaborators** (or `gh api` invitation by email).
2. Look up their numeric user id: `https://api.github.com/users/<login>`.
3. Add a `bypass_actors` entry in `.github/rulesets/dev-restricted-push.json`.
4. Update the ruleset in the GitHub UI or run `scripts/setup_dev_branch_protection.sh`.
