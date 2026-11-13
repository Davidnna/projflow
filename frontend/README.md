# ProjFlow Frontend

React 19, Vite and React Router 7.

## Cloudflare Pages configuration
- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `dist`
- Production branch: `main`
- Environment variable: `VITE_API_BASE_URL`, set to the deployed Render API origin without a trailing slash.

The `public/_redirects` file provides SPA route fallback for React Router paths.

The initial interface is a branded release foundation. It does not yet provide student registration, login or academic workflow functionality.
