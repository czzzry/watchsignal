# Issue tracker: GitHub

Issues and PRDs for this repo are intended to live as GitHub issues.
Use the `gh` CLI for issue-tracker operations once a GitHub remote is configured for this repository.

## Conventions

- Create an issue with `gh issue create`
- Read an issue with `gh issue view <number> --comments`
- List issues with `gh issue list`
- Comment with `gh issue comment <number>`
- Apply or remove labels with `gh issue edit <number> --add-label` and `--remove-label`
- Close issues with `gh issue close <number>`

## Current repo note

This repository is configured to expect GitHub Issues as the long-term tracker.
The current checkout has a GitHub remote configured.
Publishing issues is still an external service change and should happen only after explicit founder approval.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Use `gh issue view <number> --comments`.
