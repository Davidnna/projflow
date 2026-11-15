# ProjFlow architecture

## 1. Architecture style

ProjFlow will remain a **modular monolith**: one Django REST Framework backend, one React frontend and one PostgreSQL database. Domain boundaries will be represented by Django applications rather than separate microservices. This keeps deployment and maintenance appropriate for a departmental undergraduate project while preserving separation of concerns.

## 2. Existing platform

| Layer | Technology | Responsibility |
|---|---|---|
| Web client | React 19, Vite, React Router | Role-specific dashboards and workflows |
| API | Django 5.2, Django REST Framework | Business rules, validation, permissions and REST endpoints |
| Relational database | Supabase PostgreSQL | Accounts, academic records, workflows, metadata and audit history |
| Object storage | Supabase Storage | Private project documents and supporting files |
| Backend hosting | Render | Django API and local NLP inference |
| Frontend hosting | Cloudflare Pages | Static React application |
| Source control/CI | GitHub and GitHub Actions | Version control, backend tests and frontend builds |

## 3. Planned Django domain boundaries

The existing `accounts` and `core` applications remain. The academic workflows should be introduced in domain-focused applications:

- `academics`: academic sessions, departmental student register, student enrolments, lecturer profiles, supervisor assignments, milestones and session deadlines.
- `projects`: project records, topic proposals, proposal versions and topic similarity analysis.
- `submissions`: chapter/final submissions, document metadata, file versions, supervisor feedback and progress reports if not housed in `academics`.
- `examinations`: defence clearance, panels, panel membership, student allocations, assessment templates, examiner scores, results and appeals.
- `notifications`: in-app notifications and per-category user preferences, with email delivery adapters.
- `audit`: immutable or append-only records for sensitive administrative and assessment actions.

These are logical boundaries. The implementation may combine closely related models where that reduces unnecessary complexity, but it must not mix unrelated business rules into `core`.

## 4. Document storage flow

1. React sends an authenticated upload request to Django.
2. Django checks the user's role and relationship to the project, validates the submission category, format, count and size, and authorises the upload.
3. The document binary is stored in a private Supabase Storage bucket.
4. PostgreSQL stores metadata and the storage object key, not the binary.
5. Downloads are authorised by Django. Private files are not exposed through permanent public URLs; use short-lived signed access after permission checks.

Supabase service-role credentials must remain server-side and must never be included in Vite environment variables or browser bundles.

## 5. Topic similarity architecture

The similarity engine runs locally in the Django infrastructure. It combines:

- lexical/keyword similarity, using a transparent vector-space method such as TF-IDF with cosine similarity; and
- semantic similarity, using an open-source sentence-embedding model and cosine similarity.

Proposal embeddings should be generated when a proposal version is created or changed and stored for reuse. Historical proposals should not be re-embedded for every new comparison. The combined score and fixed thresholds are implementation details to be calibrated against a representative corpus. A similarity flag is advisory and visible only to the assigned supervisor.

The embedding model must be selected after measuring model size, CPU/RAM consumption, inference time and detection quality on the intended Render plan. Avoid a large model that makes the API unreliable.

## 6. Authentication and cross-origin deployment note

The current 0.1.0 backend uses DRF `SessionAuthentication`, while the frontend's API helper sends requests with `credentials: "omit"` and the Django configuration has `CORS_ALLOW_CREDENTIALS = False`. This means the current foundation is not yet wired for authenticated cross-origin React workflows.

Before enabling registration, login or protected dashboards, implement and test one coherent SPA authentication strategy, including CSRF/CORS or token handling, cookie security, refresh/expiry behaviour and logout. Do not expose a partially configured authentication flow.

## 7. Security and integrity principles

- Enforce permissions in Django, not only by hiding frontend controls.
- Apply object-level checks to student projects, supervisor relationships and panel allocations.
- Keep academic storage private.
- Validate uploads server-side using size, extension and detected content type.
- Use database constraints and transactions for one-active-session, one-current-supervisor, assessment totals and result state transitions.
- Preserve history for reassignments, submissions, feedback, assessment configuration, examiner score corrections and result decisions.
- Keep all production secrets in hosting-provider environment variables.

## 8. Deployment principles

The existing Render and Cloudflare Pages deployment arrangement is retained. Render's local filesystem is ephemeral and must not be used for permanent academic documents. Database migrations must be applied in a controlled deployment step. The local NLP model must be benchmarked against available Render memory and CPU before being enabled in production.
