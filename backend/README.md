# ProjFlow Backend

Django 5.2 LTS and Django REST Framework API.

- Custom user model: `apps.accounts.User`
- Authentication identifier: email address
- Primary keys: UUID
- Global roles: Administrator, Project Coordinator, Lecturer and Student
- Production database: Supabase PostgreSQL
- SQLite is used only as a local/test fallback when `DATABASE_URL` is absent.

## Public endpoints
- `GET /api/health/` — process health check
- `GET /api/ready/` — database readiness check

All other DRF endpoints require authentication by default.

## Deployment
Render reads the root-level `render.yaml`. Production secrets and database credentials must be configured in Render environment settings. The Render start command applies migrations before starting Gunicorn. This is suitable for the initial free-tier foundation; use a dedicated pre-deploy migration step if the service moves to a plan that supports Render pre-deploy commands.
