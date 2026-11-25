# ProjFlow

**From Proposal to Final Defence.**

ProjFlow is a web-based final-year project management system for one academic department. It is designed to coordinate student onboarding, academic sessions, supervisor allocation, project-topic approval, supervision, submissions, progress monitoring, final defence, assessment and result publication.

- **Current release:** `1.0.1-rc.1` (role-integrity and deployment-hardening candidate)
- **Project type:** Single-department academic management platform
- **Architecture:** Modular monolith
- **Repository:** <https://github.com/Davidnna/projflow>

This README is the repository's sole Markdown document. It contains the software overview, architecture, agreed requirements, local development instructions and deployment guidance.

## 1. Current implementation status

Release `0.1.0` established the branded React application, Django API, custom user model, global roles, health endpoints and deployment foundation. Release `0.2.0` introduced the academic administration backend modules. Release `0.3.0` added the authenticated React workspace and operational interfaces for the existing APIs. Release `0.3.1` adds secure one-time initial Administrator provisioning through the live application. Release `0.3.2` removes calendar dates from academic session administration and makes session activation/closure fully manual. Release `0.3.3` completes roster-based student verification by comparing every populated departmental identity field. Release `0.3.4` simplifies user-facing messages, removes public technical status and initial-setup pages, and limits student registration responses to information students need. Release `0.3.5` expands the public website with dedicated About, Features and How It Works pages, clear navigation, mobile navigation, role descriptions, workflow guidance and FAQs. Release `0.3.6` introduces student project-topic proposals, supervisor-only decisions, resubmission history and role-specific topic workspaces. Release `0.3.7` adds a supervisor topic register with separate views for awaiting review, approved, revision-requested, rejected and all assigned topic records. Release `0.3.8` adds local hybrid keyword and semantic similarity analysis across historical proposals, supervisor-only similarity reports, cached revision embeddings and deployment-time model preparation. Release `0.3.9` adds Coordinator-defined session milestones, student progress reports, supervisor assessments, revision requests and report history. Release `0.3.10` adds an Administrator-managed Coordinator Access page for granting and revoking the Project Coordinator role while preserving Coordinator-only milestone management. Release `0.3.11` fixes a student progress page rendering error by deriving academic-session availability from the milestone session status and preventing submissions or revisions when the session is not active. Release `0.3.12` replaces the student milestone-report interpretation with a chapter-by-chapter project report workflow: Coordinator-configured report sections, separate PDF/DOCX uploads, private Supabase Storage, optional submission notes, supervisor approval/revision decisions, version history and sequential section unlocking. Release `0.3.13` improves private report-storage diagnostics by logging sanitized Supabase HTTP status/error details and configuration state without exposing credentials or uploaded document content. Release `0.3.14` corrects the project-report submission API parser configuration so document uploads continue to accept multipart/form data while supervisor review actions also accept JSON requests; the CI-only Django signing key is lengthened to remove the JWT key-strength warning. Release `0.3.15` preserves the submitted document filename, including Unicode characters, in the report revision record and signed download response; downloads are forced as attachments with the original filename and start from the current page without opening a blank tab.

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


### Implemented in 0.3.6 (project topic submission and supervisor review)

- Verified students can submit an individual project proposal only after a supervisor has been assigned in the active academic session.
- Each proposal captures the project title, abstract, problem statement, research objectives and keywords.
- A student may have one current proposal at a time. A rejected proposal is retained in the history and a new proposal may then be submitted.
- The currently assigned supervisor alone can approve a submitted topic, request revision or reject it. The Project Coordinator and Administrator cannot make the supervisor's topic decision.
- Revision requests require written feedback. Students can revise and resubmit a proposal when changes are requested.
- Each submission is retained as a numbered revision, and each supervisor decision is retained with the revision reviewed, reviewer, decision and feedback.
- Supervisor reassignment transfers responsibility for the student's current proposal to the new supervisor while preserving earlier review records.
- Student and lecturer workspaces include project-topic submission and topic-review pages.
- Topic records retain all submitted proposals and statuses for comparison across academic sessions.

### Implemented in 0.3.7 (supervisor topic register)

- Added a supervisor-only endpoint that returns project topics associated with the supervisor's assignments or previously reviewed by that supervisor, including approved topics.
- Expanded the lecturer topic workspace with filters for awaiting review, approved, revision requested, rejected and all topics.
- Previously reviewed proposals are available in read-only detail view, including their submission and review history; decision controls remain available only to the currently assigned supervisor for proposals awaiting review.
- The existing review queue remains limited to current submissions awaiting a supervisor decision.
- Added API tests for approved-topic visibility, historical reviewer access after reassignment, supervisor isolation and Coordinator access restrictions.

### Implemented in 0.3.8 (historical topic similarity detection)

- Added a local hybrid keyword and semantic similarity engine using FastEmbed with the `sentence-transformers/all-MiniLM-L6-v2` ONNX model. No external AI API is called.
- Compares a submitted proposal's title, abstract, problem statement, research objectives and keywords with the latest revision of each other student's historical proposal across all academic sessions, regardless of the historical proposal's status.
- Excludes the submitting student's own historical proposals from duplicate-topic comparisons.
- Combines semantic cosine similarity (70%) with lexical term/phrase overlap (30%) for each field. Overall field weights are title 25%, abstract 20%, problem statement 25%, research objectives 20% and keywords 10%.
- Uses a fixed system threshold of 62% for potential matches. Field sections scoring at least 50% are included as matched-section evidence.
- Stores embeddings against proposal revisions and stores only above-threshold matches for each analysed revision. Historical revision embeddings are generated lazily when first needed.
- Runs analysis after submission and resubmission. A supervisor can retry a check if it was unavailable.
- Exposes similarity reports only to the currently assigned supervisor. Students, Project Coordinators, Administrators and previous supervisors cannot access the report endpoint.
- Reports show the historical title, academic session, project status, overall score and short excerpts from matched sections. Full historical proposal documents are not exposed.
- Similarity scores are advisory indicators, not proof of plagiarism and not automatic approval/rejection decisions.
- The Render build prepares the model cache before deployment; `.model_cache/` is excluded from Git.


### Implemented in 0.3.9 (legacy milestone progress monitoring)

- This release introduced a common ordered milestone structure for each academic session. In 0.3.12, the live student/supervisor workflow was replaced by chapter-by-chapter report submissions; the original milestone tables and API remain only for historical compatibility.
- Milestones contain a title, description, expected achievement, sequence number and optional due date. Academic session start/end dates remain unnecessary; milestone due dates are independently optional.
- Students with verified enrolment and a current supervisor submit one progress report per milestone, describing completed activities, challenges and next steps.
- The assigned supervisor reviews each report, records an assessment (on track, needs attention, behind schedule or milestone completed), and provides feedback. A supervisor can request a revision; revision requests require feedback.
- Students can resubmit a report when revision is requested. Numbered report revisions and supervisor assessment history are retained.
- Students can access only their own milestones and progress reports. Lecturers can access reports for their currently assigned students and records they previously reviewed. Coordinators manage milestone definitions but do not access individual progress report content through the progress-report API.
- Milestones with existing reports cannot have their session, order, title or expected achievement structure changed. They can be deactivated while their historical records remain available.
- Student, supervisor and Coordinator workspaces include role-specific progress and milestone pages.

### Implemented in 0.3.11 (student progress page reliability)

- Fixed a frontend runtime error on the student Project Progress page caused by an undefined academic-session status variable.
- The page now reads the session status exposed by the milestone API and uses it to determine whether new progress reports or revisions can be submitted.
- Historical progress reports and supervisor feedback remain visible when a session is not active; submission actions are disabled until the session is active.

### Implemented in 0.3.13 (private document storage diagnostics)

- Storage configuration failures identify only the missing environment-variable names in backend logs; secret values are never logged.
- Supabase Storage HTTP failures log the request operation, HTTP status, provider error code/message and which configured key variable was selected. API keys, bearer credentials and uploaded document contents are excluded.
- Network failures log the operation and exception type without exposing connection credentials.
- Private-bucket metadata failures are logged with the privacy field state so a missing or public bucket can be distinguished from an authentication failure.
- Student-facing upload errors remain concise and do not expose provider or infrastructure details.

### Implemented in 0.3.14 (project report review request compatibility)

- The project-report submission API now accepts JSON in addition to multipart form data and URL-encoded form data. This allows supervisor approve/request-revision actions to use JSON while student document uploads continue to use multipart requests.
- The two CI failures in supervisor report approval and revision-request tests are addressed by enabling the JSON parser on the report-submission viewset.
- The CI-only Django secret is lengthened to meet the minimum recommended HMAC key length and avoid JWT signing-key warnings in automated tests.

### Implemented in 0.3.15 (original report filenames and direct downloads)

- Preserves the uploaded document's original filename in each immutable report revision, including Unicode letters and punctuation, while removing path components and control characters.
- Generates private Supabase signed download URLs with the original filename in the `download` query parameter. Supabase responds with an attachment disposition so PDF and DOCX files download instead of opening in a blank browser tab.
- Student and supervisor download actions use a temporary in-page link. They do not open a new tab or navigate away from the report workspace.
- Retains the existing private bucket, five-minute signed URL expiry and Django object-level access checks. The random internal Storage object key remains separate from the user's original filename.
- Adds regression tests for Unicode filename retention, signed URL download-name encoding and the report download API contract.

### Implemented in 0.3.12 (chapter-by-chapter project report submissions)

- Replaced the milestone interpretation in the student-facing project progress page with a project report workspace organised by report sections.
- The Project Coordinator configures one shared report structure per academic session. A suggested eight-section template covers Preliminary Pages, Chapters One to Five, References and optional Appendices; the Coordinator can adjust it before students submit.
- Students submit each report section separately as a PDF or DOCX document, up to 20 MB, with an optional note for the assigned supervisor.
- The assigned supervisor can download each version, approve a section or request a revision with mandatory feedback. A required next section is unlocked only after the previous required section is approved.
- Each resubmission creates a new immutable document version. Original file names, file sizes, notes, timestamps and supervisor review history are retained.
- Report documents are stored in a private Supabase Storage bucket. The Django backend uses a server-side Supabase secret key (with legacy `service_role` key fallback) and returns five-minute signed download URLs only after checking the authenticated student's or supervisor's access.
- Students can access only their own report sections and submissions. Supervisors can access submissions from currently assigned students and submissions they previously reviewed. Administrators and Project Coordinators cannot access individual report documents through these APIs.
- Existing milestone and progress-report tables and endpoints are retained as legacy records; the current student and supervisor interfaces use the new report-section workflow.

### Release 1.0.0-rc.1 (consolidated project completion)

This release candidate extends the working 0.3.15 release with the remaining core project-cycle workflows. It retains all existing migrations, user records, private report objects and document revision history. Migration `projects/0005_completion_workflows.py` adds new tables and nullable/blank annotation metadata; it does not reset the database. The release is intended for departmental acceptance testing, not an assertion that production validation has already passed.

| Module | Implemented workflow |
|---|---|
| Supervision | Optional annotated PDF/DOCX uploads on supervisor decisions; authorised direct download of the exact annotated version. |
| Deadlines | Session-wide topic/final/defence deadlines and individual chapter due dates, extension requests, Coordinator decisions and effective deadlines. Deadline status is advisory; late submissions are not automatically prohibited. |
| Completion | Complete PDF/DOCX report submission after topic and all required section approvals, immutable report versions, supervisor recommendation/revision and Coordinator clearance. |
| Defence | Session-specific panels, active examiner selection, student allocation, date/time and venue, supervisor exclusion and exact-time examiner collision checks. Panel membership is immutable after allocation; a different panel may be allocated before any scores exist. |
| Assessment | One supervisor assessment structure per session, component maxima sum to 100, frozen structure per allocated defence, bounded independent examiner marks and complete correction rounds. |
| Results | Coordinator-only aggregate review, correction, explicit approval and publication; students see published component averages and total only. |
| Appeals | 14-day window from first publication, panel response, Coordinator determination, recorded score correction and republication. Previously published scores remain visible until corrected results are published. |
| Notifications | In-app inbox and per-category channel preferences; optional SMTP email delivery after committed events. |
| Dashboards | Role-scoped completion summary, searchable project progress register, deadlines/extensions, assessment, panels and results in the Final project & defence workspace. |

Existing decisions take precedence over earlier draft requirements: sequential report-section approval, PDF/DOCX only, 20 MB per uploaded document, and manual academic session activation/closure. Annotated feedback consists of uploaded corrected documents rather than a browser document editor. Other historical file formats, inline annotation editing and supporting-file bundles are not included in this candidate. Email delivery is optional and requires a working SMTP service; it is not verified by deploying the application alone. Final go-live requires passing CI, live acceptance testing, production backup and security review.

### Release 1.0.1-rc.1 (role integrity, independent result approval and deployment hardening)

This hotfix strengthens the academic role boundary and examination independence identified during the 1.0.0 RC1 audit. It retains the existing account, enrollment, supervision, report, assessment and result history. Migration `accounts/0003_enforce_student_lecturer_exclusivity.py` first normalises any conflicting legacy accounts, safely reopens affected defence workflows where an invalid examiner was already allocated, then installs database triggers for PostgreSQL and SQLite. It does not delete student enrollments, report documents, score records or historical supervisor assignments.

- A Student account cannot receive the Lecturer role. A Lecturer account cannot receive the Student role. The boundary is enforced in the `UserRole` model and by database triggers, including bulk inserts and queryset updates.
- An account with any StudentEnrollment cannot receive the Lecturer role or create/retain an active Lecturer profile. An account with an active Lecturer profile cannot receive the Student role or be enrolled as a student. The model layer and database triggers enforce these rules.
- Existing conflicting records are migrated safely: the Lecturer role is removed from any account with a Student role or student enrollment; enrolled accounts are guaranteed the Student role; its Lecturer profile is deactivated; any current supervisor assignments through that profile are closed with a migration note and both the affected student and Coordinator are notified. If an affected profile was on an examination panel, that panel member is removed, the affected project is placed in `panel_reallocation_required`, and the Coordinator and student are notified. The previous panel, score rows, published result and panel details are retained in the project workflow event; the project is moved to a new score round so old marks are not counted in the replacement assessment. Historical assignment rows and student academic records remain intact. The Coordinator must reassign affected supervisors and examination panels before proceeding. This controlled recovery path also works for closed sessions with affected projects: supervisor reassignment, assessment setup, panel creation and rescheduling are enabled only for those projects; other historical session actions remain read-only.
- A current or former supervisor cannot be allocated to that student's examination panel. Historical supervisors cannot submit marks, review appeals as an examiner or see the project through the examiner workspace.
- A Coordinator who is a member of the project's examination panel or has submitted any examiner score for that project cannot approve, return or publish its result, or decide its appeal. The conflicting Coordinator also does not receive those actions in the workspace.
- Production HTTPS responses use HSTS with a one-year max-age. HSTS subdomain inheritance and preload remain disabled to avoid imposing policy on unrelated shared hosting subdomains.
- Render now uses `/api/ready/` as its health check. This endpoint verifies database connectivity, so a running web process with an unavailable database is not marked ready.
- Regression coverage includes model-level role rejection, database-trigger rejection of bulk role writes, StudentEnrollment/LecturerProfile boundary checks, former-supervisor panel and scoring conflicts, Coordinator/examiner result separation, HSTS response headers and database readiness failure handling.

The release is an acceptance candidate until GitHub Actions passes the full Django suite and frontend build, the Render migration completes, and the live role workflows are verified. The current suite contains 132 authored test methods across 17 test classes.

## 2. Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React 19, Vite, React Router 7 | Web interface and role-specific workflows |
| Backend | Django 5.2, Django REST Framework | Business rules, validation, authentication and REST API |
| Document storage | Private Supabase Storage | Student report documents and time-limited authorised downloads |
| Authentication | Simple JWT | Short-lived access tokens and rotating refresh tokens |
| Database | Supabase PostgreSQL | Accounts, academic records, workflow state and audit history |
| Local database fallback | SQLite | Local development and automated tests when `DATABASE_URL` is absent |
| Spreadsheet import | openpyxl and Python CSV | XLSX and CSV roster parsing |
| Local NLP inference | FastEmbed 0.9.1, ONNX Runtime and `sentence-transformers/all-MiniLM-L6-v2` | Local semantic embeddings for project-topic similarity; no external AI API |
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
│   │   ├── projects/
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

A user may hold more than one compatible global role. Student and Lecturer are mutually exclusive: an account with the Student role or any student enrollment cannot hold the Lecturer role or an active Lecturer profile. A Lecturer account cannot be enrolled as a student. These boundaries are enforced by the application and database, not merely by the interface. API access is checked by Django; hiding a frontend control is not an access-control mechanism.

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

### 5.3 Project topics and supervision

- Students independently submit project topics after a supervisor has been assigned. The proposal includes a title, abstract, problem statement, research objectives and keywords.
- Only the currently assigned supervisor approves, requests revision or rejects a topic. The Project Coordinator does not make topic decisions.
- A revision request must include written feedback. The student can revise and resubmit, with each submitted version and supervisor decision retained in the history. A rejected proposal remains in the historical record, and the student may submit a new proposal.
- Potentially similar topics will be compared against all submitted proposals from current and previous academic sessions, regardless of approval status. The comparison covers title, abstract, problem statement, research objectives and keywords. A local hybrid keyword/semantic engine (no external AI API) will use fixed system thresholds. The assigned supervisor alone will see potential matches, similarity percentages, previous project title/session/status and matched sections; complete historical project documents will not be exposed. Similarity findings will be advisory and will not automatically reject a proposal.
- Students submit report sections in the Coordinator-defined sequence. Approval of earlier required sections (and any submitted optional sections) unlocks subsequent sections.
- Supervisors provide both written feedback and annotated document uploads.

### 5.4 Milestones and progress monitoring (implemented in 0.3.9)

- The Project Coordinator defines one common ordered milestone structure for all students in each academic session. Supervisors cannot add individual milestones.
- Each milestone includes a title, description, expected achievement and sequence number. A due date may be configured independently; academic session start and end dates are not required.
- Students with verified enrolment and an assigned supervisor submit a progress report for each milestone. A report describes completed activities, challenges encountered and planned next steps.
- The assigned supervisor reviews each report, records an assessment (on track, needs attention, behind schedule or milestone completed) and provides feedback. The supervisor may request a revision with mandatory feedback.
- Students can resubmit reports when revisions are requested. Numbered report revisions and supervisor review history are retained.
- Progress reports currently contain text fields only. Supporting-file uploads are deferred until private persistent document storage is integrated; Render's ephemeral filesystem is not used for student documents.
- Students see their own reports and feedback. Supervisors see reports for their assigned students and historical reports they reviewed. The Coordinator manages the common milestone structure but does not access individual progress report content through the progress-report API.

### 5.5 Project deadlines and extensions

- The Project Coordinator sets project-topic, chapter, final-submission and defence-related deadlines for each session. Students may request individual extensions before or after the original deadline, with a mandatory justification and proposed new date. The Coordinator approves or rejects each request; a request does not itself change the deadline.

### 5.6 Final submission, defence and results

1. The student submits the complete project to the supervisor.
2. The supervisor recommends or declines to recommend the student for defence.
3. The Project Coordinator gives or withholds final departmental clearance. If clearance is withheld, the student can submit a revised complete document for another supervisor recommendation.
4. The Coordinator creates examination panels, assigns lecturers and allocates cleared students.
5. A student's supervisor cannot sit on the panel examining that student's project.
6. Each panel member independently scores every configured assessment component.
7. The system calculates the average for each component and the overall mark out of 100.
8. If a discrepancy is identified before publication, the Coordinator returns the result to the panel. Each examiner may correct only their own submitted scores; ProjFlow recalculates the result.
9. The Project Coordinator approves results before publication.
10. Students see the overall score and component averages, not individual examiner scores.
11. Students may appeal within 14 days of publication. The panel reviews the complaint and the Coordinator makes the final decision. Any approved appeal-related score change follows the recorded correction and Coordinator-approval process.

Each supervisor configures one assessment structure for all students assigned to that supervisor in the academic session. Component maxima are positive integers and must sum to exactly 100. The supervisor configures the structure but does not award the marks; examination panel members do. The structure is snapshotted at allocation. Scores accept up to two decimal places. Each correction round requires every panel member to submit or reconfirm their own marks. Averages use unrounded underlying scores; displayed component averages and total are independently rounded to two decimal places. Once a result has been published, permitted appeals and their correction rounds remain available even if the session is closed.

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
| `POST` | `/api/academics/sessions/` | Create a planned session (Project Coordinator only) |
| `GET` | `/api/academics/sessions/{id}/` | Retrieve a session |
| `PATCH` | `/api/academics/sessions/{id}/` | Update planned-session details |
| `POST` | `/api/academics/sessions/{id}/activate/` | Activate a planned session |
| `POST` | `/api/academics/sessions/{id}/close/` | Close the active session |

A second session cannot be activated until the current active session is closed. Session records are retained and cannot be deleted through the API. Session status is changed only through the explicit activate and close actions.

### Departmental student roster

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/academics/roster/` | List roster records (Project Coordinator only) |
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
| `POST` | `/api/academics/enrollments/{id}/review/` | Approve or reject a pending registration (Project Coordinator only) |

Student registration requires an active academic session. Passwords must be at least 12 characters and pass Django's configured password validators. A student cannot register the same matriculation number twice in one session. The React registration interface is available in release 0.3.0. After submission, the student receives the registration status and can sign in to monitor verification.

### Lecturer accounts and supervisor allocation

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/academics/lecturers/` | List lecturer profiles for authorised users |
| `POST` | `/api/academics/lecturers/` | Create lecturer account and profile (Project Coordinator only) |
| `GET` | `/api/academics/lecturers/{id}/` | Retrieve a lecturer profile |
| `PATCH` | `/api/academics/lecturers/{id}/` | Update profile or active status |
| `DELETE` | `/api/academics/lecturers/{id}/` | Deactivate lecturer profile (soft deactivation) |
| `GET` | `/api/academics/lecturer-workloads/` | List active lecturers ordered by active supervisee count |
| `GET` | `/api/academics/supervisor-assignments/` | View assignment history allowed by role |
| `POST` | `/api/academics/supervisor-assignments/assign/` | Assign a supervisor (Project Coordinator only) |
| `POST` | `/api/academics/supervisor-assignments/{id}/reassign/` | Reassign with a mandatory reason (Project Coordinator only) |

### Project-topic proposals and supervisor review

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/projects/topics/` | List project topics available to the authenticated role |
| `POST` | `/api/projects/topics/` | Submit a new proposal (verified student with a current supervisor) |
| `GET` | `/api/projects/topics/mine/` | List the authenticated student's proposals and history |
| `GET` | `/api/projects/topics/review-queue/` | List submitted proposals assigned to the authenticated lecturer |
| `GET` | `/api/projects/topics/{id}/` | Retrieve an accessible proposal and its revision/review history |
| `POST` | `/api/projects/topics/{id}/resubmit/` | Resubmit a proposal after a supervisor requests revision |
| `POST` | `/api/projects/topics/{id}/review/` | Approve, request revision or reject (currently assigned supervisor only) |
| `GET` | `/api/projects/topics/{id}/similarity-report/` | Retrieve historical topic similarity findings (currently assigned supervisor only) |
| `POST` | `/api/projects/topics/{id}/run-similarity/` | Run or retry similarity analysis (currently assigned supervisor only) |

A proposal requires a title, abstract, problem statement, research objectives and at least one keyword. A student must have a verified enrolment in the active session and a current supervisor assignment before submitting. A revision request or rejection must include supervisor feedback. Each submission is saved as a numbered revision. A rejected proposal remains in the historical record and no longer blocks a new proposal. A student may have only one current proposal per enrolment. Reassigning a supervisor transfers the current proposal to the new supervisor; earlier review records remain linked to the supervisor who made each decision.

Similarity analysis runs after each new submission or resubmission. It compares the five proposal elements against the latest revision of each other student's topic across current and previous academic sessions, including approved and rejected topics. The engine combines local semantic embeddings and lexical term/phrase matching. The fixed threshold is 62%; only matches at or above that threshold are retained. The supervisor-only report includes the previous topic title, academic session, status, overall similarity score and relevant matched-section excerpts. Similarity scores are advisory and do not make academic decisions. If a proposal predates this feature or an analysis was unavailable, the currently assigned supervisor can run the check from the proposal detail view.


### Coordinator access

Administrators can grant or remove the Project Coordinator role for active Administrator and Lecturer accounts from the Coordinator Access page. A staff member must sign in again after a role change. Project milestone creation and modification remain restricted to accounts with the Project Coordinator role.

## Project milestones and progress monitoring

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/projects/milestones/` | List milestones available to the authenticated role/session |
| `POST` | `/api/projects/milestones/` | Create a session milestone (Project Coordinator only) |
| `PATCH` | `/api/projects/milestones/{id}/` | Update a milestone or change its availability (Project Coordinator only) |
| `GET` | `/api/projects/progress-reports/` | List the student's own reports or reports accessible to the assigned supervisor |
| `POST` | `/api/projects/progress-reports/` | Submit a report for a milestone (verified student with current supervisor) |
| `GET` | `/api/projects/progress-reports/{id}/` | Retrieve an accessible report and its revision/review history |
| `POST` | `/api/projects/progress-reports/{id}/resubmit/` | Resubmit after a supervisor requests revision |
| `POST` | `/api/projects/progress-reports/{id}/review/` | Assess a report or request revision (currently assigned supervisor only) |

A student can submit one report per milestone in their academic session. If a supervisor requests revision, the student can submit a new numbered revision without losing the previous submission or review history. Milestone order is unique within a session. Milestone records are not deleted; the Coordinator can deactivate them. Once a milestone has progress reports, its session, order, title, description and expected achievement cannot be changed, although its optional due date and availability can be updated. Individual report content is not exposed to Coordinator or Administrator progress-report endpoints.

### Completion and notification APIs (1.0.0-rc.1)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/projects/completion/?session={id}` | Role-scoped session, progress, deadline and completion workspace |
| POST | `/api/projects/completion/` | Validated workflow action; includes `action` and `session` plus action-specific fields |
| GET | `/api/projects/final-documents/{id}/download/` | Authorised signed download of a final report version |
| POST | `/api/projects/report-submissions/{id}/review/` | JSON or multipart review, with optional `annotation` file in multipart |
| GET | `/api/projects/report-submissions/{id}/reviews/{review_id}/download/` | Authorised annotated feedback download |
| GET/POST | `/api/projects/notifications/` | User-scoped notifications, read status and preferences |

Completion actions: `set_deadline`, `request_extension`, `approve_extension`, `reject_extension`, `save_scheme`, `create_panel`, `update_panel`, `submit`, `recommend`, `decline`, `clear`, `deny_clearance`, `schedule`, `score`, `return_result`, `approve_result`, `publish`, `appeal`, `review_appeal`, `accept_appeal`, `reject_appeal`. The final submission action uses multipart form data (`file`, optional `note`); other completion actions use JSON. The UI presents the available actions for each role and state; API permissions and transitions are enforced independently.

## 7. Data model introduced across releases

| Entity | Purpose and important integrity rules |
|---|---|
| `AcademicSession` | Retained academic cycles; database constraint permits only one active session |
| `StudentRosterRecord` | Departmental eligibility list; matriculation number unique per session |
| `RosterImportBatch` | Import preview/commit status and summary counts |
| `RosterImportRow` | Row-level validation results and committed record reference |
| `StudentEnrollment` | Links a user to a session and records automatic/manual verification; one matriculation number and one user enrolment per session |
| `LecturerProfile` | Lecturer staff details linked to a user account |
| `SupervisorAssignment` | Current and historical supervisor assignments; database constraint permits only one current supervisor per student enrolment |
| `ProjectTopic` | Student proposal, current supervisor responsibility and workflow status; one current proposal per enrolment |
| `ProjectTopicRevision` | Immutable numbered snapshots of each student submission |
| `ProjectTopicReview` | Supervisor decision and feedback linked to the exact revision reviewed |
| `ProjectTopicSimilarity` | Above-threshold historical match, field-level scores, threshold and model/algorithm version; visible only through the assigned-supervisor report endpoint |
| `ProjectTopicRevision.similarity_embeddings` | Private per-field semantic vectors cached for repeat comparisons; never included in API serializers |
| `ProjectMilestone` | Coordinator-defined common milestone structure for an academic session; unique order per session |
| `ProjectProgressReport` | One student report per milestone and enrolment, linked to the supervisor assignment |
| `ProjectProgressRevision` | Numbered snapshots of student progress-report submissions |
| `ProjectProgressReview` | Supervisor decision, assessment and feedback linked to the exact progress revision reviewed |
| `ProjectDeadline`, `DeadlineExtension` | Session due dates and individual extension decisions |
| `AssessmentScheme`, `DefencePanel` | Supervisor assessment template and examination panel membership |
| `ProjectCompletion`, `FinalReportVersion` | Clearance, defence allocation and final report version history |
| `ExaminerScore`, `ResultAppeal`, `CompletionEvent` | Independent marks by round, appeals and immutable workflow history |
| `ProjectNotification`, `NotificationPreference` | User-specific inbox and channel preferences |
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
- Similarity embeddings and match records are internal academic-review data. They are not returned to student or Coordinator endpoints; the similarity report is authorised only for the currently assigned supervisor.
- Academic document storage uses the existing private Supabase bucket. PostgreSQL retains document metadata and opaque object references. Django authorises each download; time-limited signed URLs retain the original filename. Section documents remain restricted to the student and current supervisor, with former supervisors limited to the versions and feedback they reviewed. Final project documents are available to the student, current supervisor, Coordinator and allocated examiners.
- PDF and DOCX are the agreed current formats; each uploaded report or annotated document may not exceed 20 MB. Document checks include extension, signature and DOCX archive validation. These checks do not constitute malware scanning; institutions should establish an appropriate endpoint/document-security policy.
- Result scores and feedback are separate from student-facing published results; examiners can retrieve only their own marks. Coordinator result review shows aggregate marks, not individual examiner scores. Every accepted score submission remains in its recorded round.
- Real student records, project documents, credentials and examination data must never be committed to this repository.

## 9. Local development setup

### 9.1 Prerequisites

Install:

- Python 3.13 (the repository pins the runtime in `backend/.python-version`).
- Node.js 24 and npm.
- Git.

A local PostgreSQL server is optional. When `DATABASE_URL` is empty, Django uses SQLite for local development and tests. Production uses Supabase PostgreSQL. `DATABASE_SSL_REQUIRE` defaults to `true` for hosted PostgreSQL; set it to `false` only when connecting to a trusted local PostgreSQL server without TLS.

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

Prepare the local semantic model once before testing topic similarity:

```bash
python manage.py warm_topic_similarity_model
```

This downloads the public model into `backend/.model_cache/`. The model runs locally through ONNX Runtime; the first preparation requires an internet connection. Render performs the same preparation during its build step.

Set the environment variables before running Django.

Linux/macOS:

```bash
export DJANGO_SECRET_KEY="replace-with-a-long-random-local-secret"
export DJANGO_DEBUG="True"
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
export CORS_ALLOWED_ORIGINS="http://localhost:5173"
export DATABASE_URL=""
export SUPABASE_URL="https://your-project-ref.supabase.co"
export SUPABASE_SECRET_KEY="sb_secret_your-private-secret-key"
export PROJFLOW_REPORTS_BUCKET="projflow-project-reports"
```

Windows PowerShell:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-local-secret"
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:5173"
$env:DATABASE_URL = ""
$env:SUPABASE_URL = "https://your-project-ref.supabase.co"
$env:SUPABASE_SECRET_KEY = "sb_secret_your-private-secret-key"
$env:PROJFLOW_REPORTS_BUCKET = "projflow-project-reports"
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
- Health check: `/api/ready/` (checks database connectivity).
- Deployment: after linked GitHub checks pass.

If the existing Render service does not automatically sync `render.yaml`, update its Health Check Path to `/api/ready/` in the Render dashboard. Confirm the HSTS environment values above are present; the production settings also default to one-year HSTS when HTTPS redirection is enabled.

Configure these environment values in Render:

| Variable | Value/source |
|---|---|
| `DJANGO_SECRET_KEY` | Generated by Render |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000` (one year) |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | `false` |
| `DJANGO_SECURE_HSTS_PRELOAD` | `false` |
| `DJANGO_ALLOWED_HOSTS` | `.onrender.com,localhost,127.0.0.1` |
| `DATABASE_URL` | Supabase Session pooler URI |
| `DATABASE_SSL_REQUIRE` | `true` (default; no additional setting required on Render) |
| `PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN` | Temporary random secret for first Administrator setup; remove after setup |
| `CORS_ALLOWED_ORIGINS` | Exact Cloudflare Pages origin |
| `CSRF_TRUSTED_ORIGINS` | Exact Cloudflare Pages origin |
| `SUPABASE_URL` | Supabase project URL from Project Settings / API |
| `SUPABASE_SECRET_KEY` | Private server-side secret key (starts with `sb_secret_`) from Supabase API Keys; never expose it in frontend settings or source control. The legacy `SUPABASE_SERVICE_ROLE_KEY` variable is accepted as a fallback. |
| `PROJFLOW_REPORTS_BUCKET` | `projflow-project-reports` |

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

### 10.6 Private Supabase Storage for project reports

The report-submission module stores student documents in a private Supabase Storage bucket. Before students upload report sections:

1. In Supabase, open Storage and create a bucket named `projflow-project-reports`.
2. Keep the bucket private; do not enable public access. Set the bucket's maximum file size to 20 MB. If the dashboard offers allowed MIME types, permit `application/pdf` and `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
3. In Supabase Project Settings / API Keys, copy the project URL and the server-side `service_role` secret key. Do not use the publishable/anon key for this backend integration.
4. In Render, set `SUPABASE_URL`, `SUPABASE_SECRET_KEY` and `PROJFLOW_REPORTS_BUCKET` in the backend service Environment settings. The bucket variable must be `projflow-project-reports` unless the bucket name is deliberately changed in both places.
5. Save the Render environment changes and wait for the service to restart. The secret key must remain on Render only; never place it in Cloudflare Pages, a `VITE_` variable, GitHub or a message. New Supabase secret keys are sent through the `apikey` header; legacy `service_role` JWT keys remain supported for older projects.

The Django API validates PDF/DOCX file signatures and size before upload. It stores opaque object paths in PostgreSQL, not public URLs. Downloads are issued through authenticated API checks and five-minute signed URLs. The backend checks that the bucket is private before upload and download. If the bucket is public, or the storage variables or bucket are not configured, document access is refused and the application displays a user-friendly message.

### 10.7 Supabase activity keep-alive workflow

The repository includes `.github/workflows/supabase-keepalive.yml`. It calls the deployed `/api/ready/` endpoint twice daily and can also be run manually. Configure the GitHub Actions repository variable `PROJFLOW_READINESS_URL` with the exact Render readiness URL after deployment. The workflow does not contain database credentials and is best-effort, not a guarantee against Supabase pausing.

### 10.8 Optional email notifications

In-app notifications work with the existing deployment and no additional variables. To enable email, configure a working SMTP provider on Render (only the backend):

| Variable | Value |
|---|---|
| `PROJFLOW_EMAIL_ENABLED` | `true` (omit or `false` to disable) |
| `EMAIL_HOST` | SMTP hostname supplied by the provider |
| `EMAIL_PORT` | Provider's SMTP port, normally 587 |
| `EMAIL_HOST_USER` | Provider login |
| `EMAIL_HOST_PASSWORD` | Provider secret |
| `EMAIL_USE_TLS` | `true` for STARTTLS |
| `DEFAULT_FROM_EMAIL` | Provider-verified sender address |

Each user can enable email for chosen categories in Notifications. Email contains a generic sign-in prompt, not private grades or attachments. Delivery is best-effort after a successful database transaction; failures are logged without credentials. Hosting plans may restrict SMTP, so verify delivery with the chosen provider before relying on it. In-app notifications remain the primary channel.

### 10.9 Release acceptance checklist (live deployment)

1. Back up the Supabase database and Storage; preserve the current 1.0.0 RC1 Git commit as a rollback point. Confirm GitHub Actions passes backend system checks, migration consistency, the full SQLite suite, the PostgreSQL 16 migration/role-integrity job and frontend build. Render should apply `accounts/0003_enforce_student_lecturer_exclusivity.py` and the existing `projects/0005_completion_workflows.py` on startup. No new bucket is needed. Confirm Render reports `/api/ready/` healthy and HTTPS responses include the configured HSTS header.
2. Sign in with Coordinator, supervisor, two other active lecturer accounts (examiners) and a verified test student. Confirm existing registrations, report sections, reviews and downloads still work. Verify a Student account is never listed or accepted as a Lecturer, and a Lecturer account cannot be enrolled as a student or given an active Lecturer profile if it already has a student enrollment. Use synthetic test records, not real marks.
3. Download a student's report with spaces/Unicode in its filename; confirm original filename and no new tab. Request revision with written feedback and an annotated PDF/DOCX. Student downloads the annotation, resubmits and receives approval; verify required sequence and version history.
4. Set topic/chapter/final/defence deadlines. Student requests an extension with a justification; confirm effective deadline changes only after Coordinator approval. Reject another request and confirm no extension. Check progress register overdue status.
5. Approve the student's project topic and all required report sections. Submit complete PDF/DOCX, request revision, resubmit, recommend and clear. Verify student cannot bypass any gate and other students cannot download the document.
6. Supervisor saves assessment components totaling 100. Reject invalid totals. Coordinator creates a panel with two other lecturers; scheduling a panel containing the current or a former supervisor must fail. Allocate a valid panel, date/time and venue. Use a near-future test appointment and submit scores after it begins. Check both assigned examiners and student see the schedule.
7. Each examiner submits marks independently. Reject excessive or repeated marks; confirm an unauthorised lecturer and any former supervisor cannot score. Verify a Coordinator who examined the project cannot approve, return or publish that result, and cannot decide its appeal. A separate eligible Coordinator can approve only after all assigned examiners submit. Return the result for correction and verify each examiner can submit only their own new marks. Compare computed averages to manual calculation.
8. Approve then publish results. Students must not see draft marks or individual examiner scores. Submit an appeal, record panel feedback, accept or reject through the Coordinator. If accepted, repeat scoring, approval and publication; verify old published result remains visible during correction.
9. Verify the Notifications inbox, unread status, category preferences and delivery if SMTP is configured. Test role-specific access, session isolation and historical record access. Confirm no secrets or private documents are exposed by API responses.
10. Close a completed test session manually, confirm ordinary writes are disabled and an otherwise eligible published-result appeal can still be processed. Record failures, repair and rerun acceptance before institutional use.

CI/runtime verification status at packaging: Python and frontend source syntax, relative frontend imports, migration trigger SQL on SQLite, standalone assessment-calculation checks and ZIP integrity checked. The full suite contains 132 authored test methods across 17 test classes. GitHub Actions now runs the full SQLite backend suite and adds a PostgreSQL 16 migration/role-integrity job to execute the production database trigger migration and focused role/completion tests. Full Django tests, migration autodetection, PostgreSQL CI and the production Vite build must pass before live acceptance. Do not treat the candidate as verified for production until these and the live acceptance tests pass.

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
