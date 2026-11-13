# Cloudflare Pages configuration

Connect `Davidnna/projflow` through Cloudflare Pages Git integration.

| Setting | Value |
|---|---|
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Environment variable | `VITE_API_BASE_URL` |

Set `VITE_API_BASE_URL` to the actual Render service origin, for example `https://projflow-api.onrender.com`, without a trailing slash.

The `frontend/public/_redirects` file provides SPA route fallback for React Router paths. Git integration triggers Pages builds and deployments on pushes to the production branch.
