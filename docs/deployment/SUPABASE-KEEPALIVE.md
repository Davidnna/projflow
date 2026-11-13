# Supabase activity keep-alive

## Purpose

Supabase Free projects may be paused after a week with too little user database activity. This workflow makes two daily requests to the existing ProjFlow database readiness endpoint.

The endpoint is `GET /api/ready/`. It executes a lightweight `SELECT 1` query through Django's configured PostgreSQL connection and returns success only when the database is reachable.

This means the request goes through the deployed application and performs a real database query. It does not expose the database password, Supabase service-role key, or database connection URI to GitHub Actions.

## Install

The workflow file is:

`.github/workflows/supabase-keepalive.yml`

It runs at 06:23 UTC and 18:23 UTC every day. In Nigeria (WAT, UTC+1), these are 07:23 and 19:23.

It also supports manual execution through the GitHub Actions **Run workflow** button.

## Configure after Render deployment

Do this only after the Render backend is deployed and its `/api/ready/` endpoint returns:

```json
{
  "status": "ready",
  "database": "connected"
}
```

In GitHub:

1. Open `Davidnna/projflow`.
2. Go to **Settings**.
3. Open **Secrets and variables** → **Actions**.
4. Select the **Variables** tab.
5. Click **New repository variable**.
6. Set the name to `PROJFLOW_READINESS_URL`.
7. Set the value to the exact Render readiness URL, for example:
   `https://YOUR-RENDER-SERVICE.onrender.com/api/ready/`
8. Save the variable.

The URL is not a credential, so a repository variable is sufficient. Do not put database passwords, Supabase service-role keys or connection strings in this variable.

## Verify

1. Open the repository's **Actions** tab.
2. Select **Supabase Activity Keep-alive**.
3. Click **Run workflow**.
4. Open the run and confirm that **Check database readiness** succeeds.
5. Subsequent scheduled runs should appear twice daily.

If the repository variable has not been configured, the job is intentionally skipped.

## Limitations

This is a best-effort activity mechanism, not a contractual guarantee against pausing.

Supabase says a few genuine database requests per day are usually enough to avoid inactivity pausing, but this is not guaranteed. A paid Supabase plan is the only documented way to ensure a project is not paused for inactivity.

GitHub scheduled workflows can be delayed or dropped during high load. GitHub also automatically disables scheduled workflows in public repositories after 60 days without repository activity. Keep an eye on the workflow's run history and re-enable it if GitHub disables it.

The workflow does not restore an already-paused Supabase project. If the project has already paused, restore it in the Supabase dashboard first, then verify the Render readiness endpoint and rerun the workflow.
