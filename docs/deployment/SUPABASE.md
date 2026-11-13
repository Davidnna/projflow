# Supabase PostgreSQL configuration

The Django backend uses Supabase PostgreSQL through `DATABASE_URL`.

For the Render-hosted persistent Django service, use the **Session pooler** connection URI copied from the Supabase Connect dialog. The shared Session pooler is the IPv4-compatible option for projects without the IPv4 add-on.

Use the URI exactly as supplied by Supabase. The backend requires SSL for a configured PostgreSQL URL. Do not use the Transaction pooler URI on port `6543` with this persistent Django configuration.

The database password is a secret. Store the full connection URI only in Render's environment settings.
