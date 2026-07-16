# Hosted Android Pilot Setup

This runbook separates work that is safe to prepare locally from actions that create or modify external services.
Do not place real passwords, tokens, database URLs, or private data in Git.

## Prepared project shape

Create two Vercel projects from the same GitHub repository.
Use `apps/web` as the root directory for the web project.
Use `apps/api` as the root directory for the API project.
Connect both projects to `main` for production and allow pull requests to create previews.

The API project uses `apps/api/app.py` as its FastAPI entrypoint.
The web project sends server-side API requests to `API_BASE_URL`.
Browser-side Taste Lab requests use authenticated same-origin Next.js routes.

## Founder-required provisioning

The founder must perform or explicitly authorize these actions after local validation passes.

1. Connect the GitHub repository to Vercel.
2. Create the web and API Vercel projects with the root directories above.
3. Create or connect one Neon PostgreSQL project.
4. Set the API project's `DATABASE_URL` to the Neon pooled connection string.
5. Generate and set one strong `BACKEND_SERVICE_TOKEN` in both Vercel projects.
6. Set `API_BASE_URL` in the web project to the API project's production URL.
7. Set `HOUSEHOLD_ACCESS_PASSWORD` and an independent `HOUSEHOLD_SESSION_SECRET` in the web project.
8. Set the existing TMDb credential and `MOVIE_NIGHT_RECOMMENDATION_SOURCE=live_tmdb` in the appropriate server projects.
9. Confirm that secrets apply to production and only to previews that genuinely need private data.

Generate independent random secrets rather than reusing the household passphrase.
Do not expose `BACKEND_SERVICE_TOKEN`, `DATABASE_URL`, or TMDb credentials through variables beginning with `NEXT_PUBLIC_`.

## Local readiness

Run the hosted gate before connecting external services.

```sh
pnpm hosted:check
```

The gate checks Android installation assets, API tests, Python compilation, and the production Next.js build.

## Migration dry run

Set `DATABASE_URL` only in the current shell or secure environment.
Run the importer without `--apply` first.

```sh
pnpm hosted:migrate -- --source data/movie_night_mediator.sqlite3
```

The dry run prints the private table names and row counts locally but does not write to Neon.
Review the inventory before applying anything.

## Migration apply

Stop normal writes to the local app before the final migration.
Run the apply command during a founder-approved migration window.

```sh
pnpm hosted:migrate -- \
  --source data/movie_night_mediator.sqlite3 \
  --apply
```

The importer creates a timestamped SQLite backup before writing.
It refuses to overwrite a non-empty PostgreSQL destination.
Use `--replace-existing` only when the backup is authoritative and replacement has been explicitly approved.
The command fails if any source and destination table counts differ.

## Production acceptance

Open the Vercel web URL in Chrome on the founder's Android phone.
Use Chrome's Install app action.
Launch WatchSignal from the new home-screen icon.
Sign in once with the household passphrase.
Turn the development computer off.
Complete setup loading, one Taste Lab save, one pass-the-phone recommendation, and one saved outcome.
Close and reopen the installed app and confirm that the state remains.

Merge a harmless visible change through a pull request with passing checks.
Confirm that the footer build identifier changes after reopening or refreshing the installed app.

## Wife phone validation

Repeat the Chrome installation and sign-in on the founder's wife's Android phone only after the founder-phone gate passes.
Confirm that both phones show the same household setup, watchlist, and saved history.
Use the phones sequentially during this phase.
Do not treat simultaneous reactions on separate phones as supported behavior.

## Upgrade triggers

Move off a free tier if cold starts interrupt normal movie-night use, quotas approach their limits, recovery needs exceed the free window, or the app becomes public or commercial.
Prefer upgrading the existing PostgreSQL service or moving the portable PostgreSQL database over redesigning product storage.
