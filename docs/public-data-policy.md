# Public Data Policy

WatchSignal supports private household profiles and taste calibration, while this repository is designed to remain safe for public review.

## What may be committed

- synthetic household profiles with fictional labels and stable test IDs
- deterministic fixture ratings and recommendation outputs created for tests
- screenshots and demos generated from the synthetic fixture set
- public movie metadata used within the documented provider and dataset terms

## What must stay local

- API keys, tokens, environment files, and deployment credentials
- SQLite databases and local profile or household state
- real household names, taste histories, ratings, watchlists, or feedback
- downloaded datasets and generated user-specific queue artifacts
- absolute workstation paths and host-specific configuration

The repository's `.gitignore` excludes private runtime data. CI also runs `scripts/check_public_data_hygiene.py` to catch common consumer mailbox addresses, machine-specific home paths, and tracked OS metadata.

The automated check is a guardrail, not proof that a dataset is synthetic. New fixtures, screenshots, and validation reports still require human review before commit.
