# ProjFlow

**From Proposal to Final Defence.**

ProjFlow is a web-based final-year project management system for one academic department. It is designed to coordinate student onboarding, academic sessions, supervisor allocation, project-topic approval, supervision, submissions, progress monitoring, final defence, assessment and result publication.

- **Current release:** `0.3.5`
- **Project type:** Single-department academic management platform
- **Architecture:** Modular monolith
- **Repository:** <https://github.com/Davidnna/projflow>

This README is the repository's sole Markdown document. It contains the software overview, architecture, agreed requirements, local development instructions and deployment guidance.

## 1. Current implementation status

Release `0.1.0` established the branded React application, Django API, custom user model, global roles, health endpoints and deployment foundation. Release `0.2.0` introduced the academic administration backend modules. Release `0.3.0` added the authenticated React workspace and operational interfaces for the existing APIs. Release `0.3.1` adds secure one-time initial Administrator provisioning through the live application. Release `0.3.2` removes calendar dates from academic session administration and makes session activation/closure fully manual. Release `0.3.3` completes roster-based student verification by comparing every populated departmental identity field. Release `0.3.4` simplifies user-facing messages, removes public technical status and initial-setup pages, and limits student registration responses to information students need. Release `0.3.5` expands the public website with dedicated About, Features and How It Works pages, clear navigation, mobile navigation, role descriptions, workflow guidance and FAQs.

### Implemented in 0.2.0 (backend)

- Academic session creation, activation and closure through the backend API.
- Database enforcement of one active academic session at a time.
- Departmental student roster API for manual entry and CSV/XLSX import.
- Spreadsheet import preview, row-level validation, duplicate detection and explicit commit.
- Student self-registration API using email, password and matriculation number.
- Automatic student verification when the active-session roster record and all populated identity fields match: matriculation number, first name, last name, other names (when recorded), email (when recorded), phone (when recorded) and eligibility.
- Case-insensitive name/email matching and tolerant phone formatting for harmless spaces, brackets, dots and hyphens.
- Manual registration review only for missing roster records, ineligible records or identity-field mismatches, with mismatch reasons retained for the review team.
- Student phone number and verification explanation retained on the enrollment record for authorised review.
- Lecturer account and profile API for creation by an Administrator or Project Coordinator.
- Supervisor allocation to verified students in the active academic session.
- Lecturer workload visibility, ordered from the lowest active supervisee count.
- Supervisor reassignment with a mandatory reason and preserved assignment history.
- JWT access and refresh authentication for the separately hosted React frontend.
- Role-based API permissions for academic administration operations.
- Django administration screens for the new academic records.

### Implemented in 0.3.0 (frontend)

- Public overview and platform information pages.
- Student login and self-registration interfaces connected to the Django API.
- JWT access-token handling, refresh-token rotation and authenticated route protection.
- Role-aware workspace navigation and dashboard views for Administrators, Project Coordinators, Lecturers and Students.
- Coordinator academic session management, including name-only creation and manual activation/closure without calendar-date requirements.
- Student roster management with manual record entry and CSV/XLSX import preview and commit.
- Student registration review with approve/reject decisions and rejection reasons.
- Lecturer account creation and lecturer directory.
- Supervisor allocation, lecturer workload visibility and supervisor reassignment with a mandatory reason.
- Responsive desktop and mobile layouts for the public site and authenticated workspace.


### Implemented in 0.3.1 (initial system provisioning)

- One-time public setup status endpoint and React setup page for creating the first Administrator account directly in the production database.
- A high-entropy temporary setup secret is required; the backend compares it securely and rate-limits anonymous setup requests.
- The endpoint creates a Django superuser and automatically assigns the ProjFlow Administrator role.
- Database locking and an existing-administrator check prevent the initial setup route from creating a second first Administrator.
- The setup route becomes unavailable after the first Administrator role assignment exists.

### Implemented in 0.3.2 (manual academic session lifecycle)

- Academic sessions are created using a session name only; start and end dates are not required or shown in the application.
- The Project Coordinator manually activates and closes sessions when departmental operations are ready.
- No academic session transition is triggered automatically by calendar dates.
- Only one academic session may be active at a time, and previous sessions remain available for historical records.
- Existing session date values are preserved as nullable legacy metadata; they do not control session status.

### Implemented in 0.3.3 (complete student roster verification)

- Student self-registration compares the matriculation number against the active academic session's roster.
- The system also compares first name and last name, and compares other names, email and phone whenever those values are populated in the departmental roster.
- Name and email comparisons ignore letter case and repeated/leading/trailing whitespace. Phone comparison ignores harmless spaces, brackets, dots and hyphens.
- A roster record marked ineligible cannot be automatically verified.
- Exact eligible matches are automatically verified without Administrator or Coordinator approval.
- Missing roster records, ineligible records and mismatches are sent to the manual review queue with a concise explanation of the mismatch.
- The registration form collects the phone number where it is present in the departmental register and explains that names/contact details must match the roster.

### Implemented in 0.3.4 (user-facing information cleanup)

- Removed public pages that exposed API, database, hosting or release details.
- Removed the completed initial Administrator setup page from normal site navigation; the old setup URL now returns users to sign-in.
- Replaced release labels and development-roadmap notices with concise, task-focused descriptions.
- Student-facing registration responses and enrollment endpoints expose only the student's name, matriculation number, academic session and registration status; internal verification notes, method and review metadata remain restricted to authorised staff records.
- General service errors no longer disclose deployment configuration or internal server details.
- Public health/readiness checks retain their operational function without returning service version or database-provider status.
- Enrollment records retain the submitted phone number and verification explanation.

### Implemented in 0.3.5 (expanded public website)

- Expanded the public homepage with a clear product introduction, current platform capabilities, departmental workflow, user roles and common questions.
- Added dedicated About ProjFlow, Features and How It Works pages accessible before sign-in or registration.
- Added responsive public navigation and a structured footer with links to public information and account access.
- Described only capabilities available in the current release; project-topic proposals, submissions, progress monitoring, defence and assessment are not represented as live features.
- Updated page metadata and the frontend package version.

### Not implemented yet

The following modules are planned for later development and must not be treated as operational features in this release:

- Project-topic proposals, supervisor topic decisions and local topic-similarity analysis.
- Chapter and final-project submissions, private Supabase Storage integration and annotated feedback.
- Coordinator-defined project milestones, progress reports, deadlines and extension requests.
- Final-project recommendation and departmental defence clearance.
- Examination panels, defence scheduling and supervisor conflict-of-interest checks.
- Supervisor-configured assessment templates, examiner scoring, result approval, publication and appeals.
- In-app and email notifications with user-controlled preferences for each notification category.
- Advanced project-specific dashboards for topic review, submissions, progress monitoring, examinations and results.

## 2. Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React 19, Vite, React Router 7 | Web interface and role-specific workflows |
| Backend | Django 5.2, Django REST Framework | Business rules, validation, authentication and REST API |
| Authentication | Simple JWT | Short-lived access tokens and rotating refresh tokens |
| Database | Supabase PostgreSQL | Accounts, academic records, workflow state and audit history |
| Local database fallback | SQLite | Local development and automated tests when `DATABASE_URL` is absent |
| Spreadsheet import | openpyxl and Python CSV | XLSX and CSV roster parsing |
| Backend hosting | Render | Django API and application services |
| Frontend hosting | Cloudflare Pages | Static React application |
| Source control and CI | GitHub and GitHub Actions | Version control, automated tests and production builds |

ProjFlow remains a modular monolith: one Django backend and one React frontend. Domain boundaries are implemented as Django applications rather than separately deployed microservices.

## 3. Repository structure

```text
projflow/
├── backend/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── academics/
│   │   └── core/
│   ├── config/
│   ├── .env.example
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── .env.example
│   └── package.json
├── docs/
│   └── branding/
├── .github/
│   └── workflows/
├── render.yaml
└── README.md
```

## 4. Agreed system scope and roles

ProjFlow serves one academic department. It retains records from multiple academic sessions, but only one project cycle may be active at a time. Projects are individual; group projects are outside the approved scope.

The four global roles are:

| Role | Main responsibility |
|---|---|
| Administrator | System administration and account/role administration |
| Project Coordinator | Academic sessions, departmental student records, lecturer accounts, supervisor allocation, milestones, deadlines, defence clearance and result approval |
| Lecturer | Lecturer profile and assigned supervision/examination responsibilities |
| Student | Registration, topic proposals, project development, submissions and progress reporting |

A user may hold more than one global role. API access is checked by Django; hiding a frontend control is not an access-control mechanism.

## 5. Approved academic workflow

### 5.1 Academic sessions and student onboarding

1. The Project Coordinator creates an academic session using its name; no start or end dates are required.
2. The Coordinator manually activates the session when the department is ready. Only one session may be active at a time; the Coordinator closes it manually when the project cycle is complete.
3. The Coordinator imports student records through CSV/XLSX or enters them individually.
4. A student self-registers with an email address, password, matriculation number, names and phone number where applicable.
5. ProjFlow checks the matriculation number against the active session's departmental roster and compares all populated roster identity fields.
6. An eligible record with matching first name, last name and any recorded other names, email and phone number is automatically verified.
7. A missing, ineligible or inconsistent record is referred for manual review by the Project Coordinator, with the reason recorded.
8. Only verified students can be allocated a supervisor.

The Coordinator can approve or reject a registration requiring manual review. Rejection requires a reason. Pending students can authenticate to check their registration status, but future project actions must enforce verified-enrolment permissions.

### 5.2 Supervisor allocation

- The Project Coordinator assigns a supervisor before the student submits a project topic.
- Allocation is informed by the number of students already assigned to each lecturer. The system displays workload but does not automatically allocate students. Research expertise is not a mandatory allocation criterion.
- There is no fixed or system-enforced maximum supervision capacity.
- The Coordinator can reassign a student at any time during the active session.
- A reassignment reason is mandatory. The previous assignment, new assignment, date, Coordinator and reason remain in the history.

### 5.3 Project topics and supervision (planned)

- Students independently propose project topics after a supervisor has been assigned.
- Only the assigned supervisor approves, requests revision or rejects a topic.
- Potentially similar topics are compared against all submitted proposals from current and previous academic sessions, regardless of their approval status. The comparison covers title, abstract, problem statement, research objectives and keywords. A local hybrid keyword/semantic engine (no external AI API) uses fixed system thresholds. The assigned supervisor alone sees potential matches, similarity percentages, previous project title/session/status and matched sections; complete historical project documents are not exposed. Similarity findings are advisory and do not automatically reject a proposal.
- Students can submit chapters in any order; chapter approval is not a prerequisite for submitting another chapter.
- Supervisors provide both written feedback and annotated document uploads.

### 5.4 Progress monitoring (planned)

- The Project Coordinator defines one common milestone structure for all students in each academic session.
- Supervisors cannot add individual milestones.
- Students submit progress reports at milestone points. Supervisors review reports, comment and assess progress.
- The Project Coordinator sets project-topic, chapter, final-submission and defence-related deadlines for each session. Students may request individual extensions before or after the original deadline, with a mandatory justification and proposed new date. The Coordinator approves or rejects each request; a request does not itself change the deadline.

### 5.5 Final submission, defence and results (planned)

1. The student submits the complete project to the supervisor.
2. The supervisor recommends or declines to recommend the student for defence.
3. The Project Coordinator gives or withholds final departmental clearance.
4. The Coordinator creates examination panels, assigns lecturers and allocates cleared students.
5. A student's supervisor cannot sit on the panel examining that student's project.
6. Each panel member independently scores every configured assessment component.
7. The system calculates the average for each component and the overall mark out of 100.
8. If a discrepancy is identified before publication, the Coordinator returns the result to the panel. Each examiner may correct only their own submitted scores; ProjFlow recalculates the result.
9. The Project Coordinator approves results before publication.
10. Students see the overall score and component averages, not individual examiner scores.
11. Students may appeal within 14 days of publication. The panel reviews the complaint and the Coordinator makes the final decision. Any approved appeal-related score change follows the recorded correction and Coordinator-approval process.

Each supervisor configures one assessment structure for all students assigned to that supervisor in the academic session. Component maxima must sum to exactly 100. The supervisor configures the structure but does not award the marks; examination panel members do.

## 6. Academic administration API

All protected endpoints require an access token in the HTTP `Authorization` header:

```http
Authorization: Bearer <access-token>
```

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register/` | Student self-registration |
| `POST` | `/api/auth/token/` | Obtain access and refresh tokens using email and password |
| `POST` | `/api/auth/token/refresh/` | Rotate/refresh the token pair |
| `POST` | `/api/auth/logout/` | Blacklist the authenticated user's refresh token |

Access tokens expire after 15 minutes. Refresh tokens expire after 7 days and are rotated; the previous refresh token is blacklisted. Logout invalidates the submitted refresh token. An already-issued access token remains valid until its short expiry.

### Health and readiness

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health/` | Public API liveness check |
| `GET` | `/api/ready/` | Readiness check; returns HTTP 200 when the service is ready |

### Academic sessions

Academic sessions are created with a name only. Start and end dates are not required or exposed through the application API. The Coordinator manually activates and closes sessions; calendar dates never trigger lifecycle transitions. Existing date values are preserved as nullable legacy metadata.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/academics/sessions/` | List sessions |
| `POST` | `/api/academics/sessions/` | Create a planned session (Coordinator/Administrator) |
| `GET` | `/api/academics/sessions/{id}/` | Retrieve a session |
| `PATCH` | `/api/academics/sessions/{id}/` | Update planned-session details |
| `POST` | `/api/academics/sessions/{id}/activate/` | Activate a planned session |
| `POST` | `/api/academics/sessions/{id}/close/` | Close the active session |

A second session cannot be activated until the current active session is closed. Session records are retained and cannot be deleted through the API. Session status is changed only through the explicit activate and close actions.

### Departmental student roster

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/academics/roster/` | List roster records (Coordinator/Administrator) |
| `POST` | `/api/academics/roster/` | Add a student record manually |
| `GET` | `/api/academics/roster/{id}/` | Retrieve a roster record |
| `PATCH` | `/api/academics/roster/{id}/` | Update a roster record |
| `POST` | `/api/academics/roster-imports/preview/` | Preview and validate a CSV/XLSX import |
| `GET` | `/api/academics/roster-imports/` | List import batches |
| `GET` | `/api/academics/roster-imports/{id}/` | Retrieve batch and row-level results |
| `POST` | `/api/academics/roster-imports/{id}/commit/` | Commit valid rows from a previewed batch |

Roster spreadsheet headers must include `matric_number`, `first_name` and `last_name`. Optional headers are `other_names`, `email`, `phone` and `is_eligible`. The importer accepts common header aliases such as `matric_no`, `matriculation_number`, `given_name` and `surname`. Matriculation numbers should be stored as text in spreadsheets to preserve leading zeros.

Example CSV:

```csv
matric_number,first_name,last_name,other_names,email,phone,is_eligible
CS/2026/001,Ada,Okafor,Chiamaka,ada@example.com,08000000001,yes
CS/2026/002,Emeka,Nwosu,,emeka@example.com,08000000002,yes
```

Imports are previewed before records are created. Invalid rows and duplicates are reported; valid rows are committed only after the Coordinator confirms the batch. CSV files must be UTF-8. XLSX parsing uses the active worksheet. Import files are limited to 10 MB and 5,000 rows. A roster import cannot be committed twice.

### Student registration and verification

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register/` | Create a student account and active-session enrolment |
| `GET` | `/api/academics/enrollments/` | List enrolments according to role and relationship |
| `GET` | `/api/academics/enrollments/mine/` | Retrieve the authenticated student's registration status |
| `POST` | `/api/academics/enrollments/{id}/review/` | Approve or reject a pending registration (Coordinator/Administrator) |

Student registration requires an active academic session. Passwords must be at least 12 characters and pass Django's configured password validators. A student cannot register the same matriculation number twice in one session. The React registration interface is available in release 0.3.0. After submission, the student receives the registration status and can sign in to monitor verification.

### Lecturer accounts and supervisor allocation

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/academics/lecturers/` | List lecturer profiles for authorised users |
| `POST` | `/api/academics/lecturers/` | Create lecturer account and profile (Coordinator/Administrator) |
| `GET` | `/api/academics/lecturers/{id}/` | Retrieve a lecturer profile |
| `PATCH` | `/api/academics/lecturers/{id}/` | Update profile or active status |
| `DELETE` | `/api/academics/lecturers/{id}/` | Deactivate lecturer profile (soft deactivation) |
| `GET` | `/api/academics/lecturer-workloads/` | List active lecturers ordered by active supervisee count |
| `GET` | `/api/academics/supervisor-assignments/` | View assignment history allowed by role |
| `POST` | `/api/academics/supervisor-assignments/assign/` | Assign a supervisor (Coordinator/Administrator) |
| `POST` | `/api/academics/supervisor-assignments/{id}/reassign/` | Reassign with a mandatory reason (Coordinator/Administrator) |

## 7. Data model introduced in Phase 1

| Entity | Purpose and important integrity rules |
|---|---|
| `AcademicSession` | Retained academic cycles; database constraint permits only one active session |
| `StudentRosterRecord` | Departmental eligibility list; matriculation number unique per session |
| `RosterImportBatch` | Import preview/commit status and summary counts |
| `RosterImportRow` | Row-level validation results and committed record reference |
| `StudentEnrollment` | Links a user to a session and records automatic/manual verification; one matriculation number and one user enrolment per session |
| `LecturerProfile` | Lecturer staff details linked to a user account |
| `SupervisorAssignment` | Current and historical supervisor assignments; database constraint permits only one current supervisor per student enrolment |
| `User`, `Role`, `UserRole` | Existing UUID-based account model, global roles and role assignments |

Sensitive changes are performed through transactional service functions. Academic session, roster, enrolment and assignment records are retained rather than silently overwritten.

## 8. Security and data-handling rules

- Django enforces role and object-level access. Frontend visibility is not a security boundary.
- Passwords are stored using Django's password hashing framework.
- JWTs are sent in the `Authorization` header; cross-origin cookie credentials are not used by the SPA API configuration. The access token is held in application memory, while the rotating refresh token and minimal user profile are kept in `sessionStorage` for the browser session.
- Production secrets and database connection strings belong in Render environment settings, never in source control.
- Student registration records are restricted according to role and relationship.
- Lecturer profile deactivation prevents new supervisor allocations while retaining the user account and historical assignments; this avoids disabling a user who may hold another global role.
- Roster imports are validated before commit and have a 10 MB/5,000-row limit.
- Future academic document storage will use private Supabase Storage buckets. PostgreSQL will store metadata and object references, not document binaries. Django will authorise every upload/download and issue short-lived access links. Access is limited to the student, their assigned supervisor, the Project Coordinator and examination panel members assigned to that student.
- Future project submissions will have one mandatory primary document and up to five optional supporting files. Each file will be limited to 20 MB. Permitted formats will be fixed by the system for each submission category and cannot be changed through the user interface: proposals/chapters/revisions/annotated feedback/final reports accept PDF, DOC and DOCX; defence presentations accept PPTX and PDF; supplementary materials accept PDF, DOC, DOCX, XLSX, JPG, JPEG and PNG.
- Real student records, project documents, credentials and examination data must never be committed to this repository.

## 9. Local development setup

### 9.1 Prerequisites

Install:

- Python 3.13 (the repository pins the runtime in `backend/.python-version`).
- Node.js 24 and npm.
- Git.

A local PostgreSQL server is optional. When `DATABASE_URL` is empty, Django uses SQLite for local development and tests. Production uses Supabase PostgreSQL.

### 9.2 Clone the repository

```bash
git clone https://github.com/Davidnna/projflow.git
cd projflow
```

### 9.3 Configure and run the backend

Open a terminal in the repository root, then:

```bash
cd backend
python -m venv .venv
```

Activate the environment.

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Set the environment variables before running Django.

Linux/macOS:

```bash
export DJANGO_SECRET_KEY="replace-with-a-long-random-local-secret"
export DJANGO_DEBUG="True"
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
export CORS_ALLOWED_ORIGINS="http://localhost:5173"
export DATABASE_URL=""
```

Windows PowerShell:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-local-secret"
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:5173"
$env:DATABASE_URL = ""
```

Apply database migrations and create a local-only development Administrator account:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The backend is available at `http://127.0.0.1:8000/`. Django's `create_superuser` automatically assigns the Administrator role. To create a Project Coordinator, create the account in Django administration and assign the seeded `project_coordinator` role through the UserRole administration screen.

The `createsuperuser` command in this section is for a local development database only. For the deployed production Administrator, use the live one-time setup process in section 10.2. The `.env.example` files are templates; Django does not automatically load them. Set environment variables in the terminal, your IDE run configuration or your hosting provider.

### 9.4 Configure and run the frontend

Open a second terminal in the repository root:

```bash
cd frontend
npm install
```

Create `frontend/.env` with:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the Vite development server:

```bash
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173/`.

### 9.5 Run backend checks and tests

From the `backend` directory, with the virtual environment active and the environment variables configured:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Build the frontend from the `frontend` directory:

```bash
npm run build
```

GitHub Actions runs the backend configuration check, migration consistency check, backend test suite and frontend production build on pushes and pull requests targeting `main`.

## 10. Deployment

### 10.1 Supabase PostgreSQL

The deployed Django service uses the Supabase PostgreSQL **Session pooler** URI copied from the Supabase Connect dialog. Use the supplied URI as `DATABASE_URL` in Render. The backend requires SSL for a configured PostgreSQL URL. Do not use the Transaction pooler URI on port `6543` with this persistent Django configuration. Keep the database password and full URI private.

### 10.2 Initial Administrator provisioning (live deployment)

The first ProjFlow Administrator was created through the deployed web application; Render Shell and local Django commands were not required. The one-time setup page is removed from the normal public site after initial provisioning. If the production database is ever recreated, restore the setup page from the initial-provisioning commit before creating the first Administrator. Before any Administrator account exists:

1. Generate a high-entropy random secret of at least 32 characters using a password manager.
2. In Render, open the ProjFlow backend service and add `PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN` under Environment. Store the secret only in Render; do not place it in GitHub, Cloudflare Pages, source code or a message.
3. Save the environment change and wait for Render to finish restarting the service.
4. Temporarily restore the initial setup page from the initial-provisioning commit, deploy it, and open `https://YOUR-CLOUDFLARE-PAGES-DOMAIN/setup/administrator` to enter the temporary secret, Administrator name, email and a strong account password. The setup request is processed by Django and writes directly to the configured production database.
5. After the page confirms success, remove `PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN` from Render Environment and save the change.
6. Sign in through the normal ProjFlow login page.

The backend refuses setup when the secret is absent or shorter than 32 characters, compares the supplied secret using a constant-time comparison, limits anonymous setup requests, validates the account password using Django's configured validators, and permits the operation only while no Administrator role assignment or Django superuser exists. The operation is transactionally protected. The setup page does not display or store the configured secret.

### 10.3 Render backend

The root `render.yaml` defines the Django service:

- Runtime: Python 3.13.
- Root directory: `backend`.
- Build: install requirements, run Django checks and collect static files.
- Start: apply migrations and start Gunicorn.
- Health check: `/api/health/`.
- Deployment: after linked GitHub checks pass.

Configure these environment values in Render:

| Variable | Value/source |
|---|---|
| `DJANGO_SECRET_KEY` | Generated by Render |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` |
| `DJANGO_ALLOWED_HOSTS` | `.onrender.com,localhost,127.0.0.1` |
| `DATABASE_URL` | Supabase Session pooler URI |
| `PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN` | Temporary random secret for first Administrator setup; remove after setup |
| `CORS_ALLOWED_ORIGINS` | Exact Cloudflare Pages origin |
| `CSRF_TRUSTED_ORIGINS` | Exact Cloudflare Pages origin |

The Render start command applies committed migrations before starting Gunicorn. This is configured for the current service plan; use a dedicated pre-deploy migration step if the hosting plan supports it.

### 10.4 Cloudflare Pages frontend

Connect the GitHub repository through Cloudflare Pages and configure:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Environment variable | `VITE_API_BASE_URL` |

Set `VITE_API_BASE_URL` to the actual Render service origin without a trailing slash. The `frontend/public/_redirects` file provides SPA route fallback for React Router paths.

After Cloudflare creates the Pages URL, set the exact origin (including `https://`, with no path or trailing slash) in both `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` on Render, then redeploy.

### 10.5 Deployment verification

- `https://YOUR-RENDER-SERVICE.onrender.com/api/health/` should return HTTP 200 and `status: ok`.
- `https://YOUR-RENDER-SERVICE.onrender.com/api/ready/` should return HTTP 200 and `database: connected`.
- The Cloudflare Pages site should load and React Router paths should resolve on refresh.

Render's free service may sleep after inactivity. Its local filesystem is ephemeral and must not be used for permanent student documents. Supabase Free has storage/compute limits and may pause projects; production use requires a documented backup and retention arrangement.

### 10.6 Supabase activity keep-alive workflow

The repository includes `.github/workflows/supabase-keepalive.yml`. It calls the deployed `/api/ready/` endpoint twice daily and can also be run manually. Configure the GitHub Actions repository variable `PROJFLOW_READINESS_URL` with the exact Render readiness URL after deployment. The workflow does not contain database credentials and is best-effort, not a guarantee against Supabase pausing.

## 11. Branding

ProjFlow's tagline is **From Proposal to Final Defence.** The product identity communicates professionalism, clarity, accountability, progress and reliability.

| Colour | Hex | Main use |
|---|---|---|
| Midnight Navy | `#101C36` | Navigation, headings and dark surfaces |
| Royal Blue | `#2563EB` | Primary actions, links and highlights |
| Teal | `#14B8A6` | Progress and positive states |
| Light Grey | `#F1F5F9` | Backgrounds and neutral surfaces |
| White | `#FFFFFF` | Content surfaces and reversed logo elements |

Montserrat is used for brand wordmarks and major brand headings. Inter is used for application interface text. SVG assets are preferred for scalable logo use; preserve the logo aspect ratio, clear space and original colours. The full initial brand guideline is retained as `docs/branding/brand-guidelines.pdf`.

## 12. Development conventions

1. Every project update must include a clear Git commit message.
2. Use four-space indentation consistently across source code.
3. `README.md` is the only Markdown (`.md`) file permitted in the repository. Add software and local-run guidance to this file rather than creating additional Markdown documents.
4. Preserve the existing application architecture and naming conventions unless a technical reason justifies a change.
5. Run relevant checks and tests before treating an implementation slice as complete.
6. Never commit secrets, real student information or private academic documents.

## 13. Licence

No open-source licence has been selected. Until a licence is added, no permission to reuse or redistribute the software should be assumed.
