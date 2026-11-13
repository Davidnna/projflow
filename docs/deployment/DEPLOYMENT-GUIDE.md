# ProjFlow v0.1.0 — Deployment Guide

This release is designed for a cloud-only workflow. You do not need to install or run Python, Node.js, Django, React or PostgreSQL on your Windows computer.

## Deployment order
1. Create a Supabase project and obtain its PostgreSQL Session pooler connection string.
2. Deploy the Django API to Render using the repository's `render.yaml`.
3. Deploy the React frontend to Cloudflare Pages.
4. Set the Cloudflare API URL and the Render CORS/CSRF origins.
5. Verify both public health endpoints and the frontend status page.

Choose Frankfurt for Supabase if available; the Render Blueprint selects Frankfurt.

## A. Supabase PostgreSQL
1. Open https://supabase.com and create a project.
2. Choose a strong database password and store it privately.
3. Choose Frankfurt if available.
4. Wait for the database to finish provisioning.
5. Open **Connect** in the Supabase project.
6. Select **Session pooler**.
7. Copy the complete PostgreSQL connection URI and keep it private.

Use the Session pooler URI, normally on port `5432`, for this persistent Django service. Do not use the Transaction pooler URI on port `6543` for this configuration. Do not paste the connection URI into GitHub, a source file, a public issue or a chat message.

## B. Render backend
1. Open https://render.com and sign in.
2. Choose **New** → **Blueprint**.
3. Connect the GitHub account if prompted.
4. Select `Davidnna/projflow`.
5. Render reads the root-level `render.yaml`.
6. Confirm the service is named `projflow-api` and the region is Frankfurt.
7. When Render requests values for unsynchronised environment variables, provide:
   - `DATABASE_URL`: the private Supabase Session pooler URI.
   - `CORS_ALLOWED_ORIGINS`: leave blank temporarily; fill it after Cloudflare creates the Pages URL.
   - `CSRF_TRUSTED_ORIGINS`: leave blank temporarily; fill it after Cloudflare creates the Pages URL.
8. Confirm creation and wait for the first deployment.

Render generates `DJANGO_SECRET_KEY` automatically. Do not replace it with a value committed to the repository.

After deployment, copy the Render service's public URL. Verify:
- `https://YOUR-RENDER-SERVICE.onrender.com/api/health/` — expected HTTP 200 and `"status": "ok"`.
- `https://YOUR-RENDER-SERVICE.onrender.com/api/ready/` — expected HTTP 200 and `"database": "connected"`.

## C. Cloudflare Pages frontend
1. Open https://dash.cloudflare.com.
2. Go to **Workers & Pages**.
3. Choose **Create application** → **Pages** → **Connect to Git**.
4. Authorise Cloudflare to access the GitHub repository if prompted.
5. Select `Davidnna/projflow`.
6. Configure:
   - Project name: `projflow` if available.
   - Production branch: `main`.
   - Root directory: `frontend`.
   - Build command: `npm run build`.
   - Build output directory: `dist`.
7. Add build environment variable `VITE_API_BASE_URL` with the actual Render service origin, e.g. `https://projflow-api.onrender.com`, without a trailing slash.
8. Deploy the project.

Cloudflare Pages should produce a public `pages.dev` URL. Copy the exact origin, including `https://`, with no path or trailing slash.

## D. Finish cross-origin configuration
Return to Render → `projflow-api` → Environment. Set both variables to the exact Cloudflare Pages origin:
- `CORS_ALLOWED_ORIGINS`: `https://YOUR-PROJECT.pages.dev`
- `CSRF_TRUSTED_ORIGINS`: `https://YOUR-PROJECT.pages.dev`

Save changes and allow Render to redeploy.

## E. Verify the deployment
1. Open the Render `/api/health/` endpoint.
2. Open the Render `/api/ready/` endpoint.
3. Open the Cloudflare Pages site.
4. Navigate to **System status**.
5. Confirm that both the API and database show as online/connected.
6. Refresh `/platform` and `/status` directly to verify React Router SPA routing.

## Free-tier limitations
Free hosting is suitable for the initial demonstration, not yet for a department's operational academic records.
- Render free web services can sleep after inactivity and take time to wake.
- Render's local filesystem is ephemeral. Do not store uploaded project files there.
- Supabase Free has storage and compute limits and may pause projects after inactivity.
- Database backups and document retention must be addressed before real student records are used.

The project will add private object storage and a verified backup process before implementing real document submissions.
