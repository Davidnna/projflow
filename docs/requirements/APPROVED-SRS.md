# ProjFlow — Approved Software Requirements Specification

**Project:** Design and Implementation of a Web-Based Final Year Project Management System  
**Product:** ProjFlow — *From Proposal to Final Defence*  
**Requirements baseline:** 1.0  
**Application foundation:** Release 0.1.0  
**Status:** Approved functional direction for implementation

## 1. Purpose

ProjFlow is a web-based system for managing the final-year project lifecycle within one academic department. It coordinates student registration, supervisor allocation, topic proposal and approval, project development, submissions, progress monitoring, final defence, assessment, result publication and appeals.

This document consolidates the requirements agreed during project planning. It is the implementation baseline; it does not claim that the described workflows are already present in release 0.1.0.

## 2. Scope and boundaries

- The system serves **one academic department**.
- It supports **individual projects only**. Each eligible student has an independent project record in an academic session.
- It supports multiple academic sessions, with **no more than one active project cycle at a time**.
- Historical sessions and their records remain available for authorised reference.
- The system manages academic and administrative project workflows. It is not a general learning-management system.

## 3. User roles and responsibilities

### 3.1 Administrator
- Performs initial system administration.
- Creates Project Coordinator accounts.
- Creates or manages lecturer accounts together with the Project Coordinator, according to assigned administrative permissions.
- Manages platform-level configuration and access.

### 3.2 Project Coordinator
- Creates and manages academic sessions and controls which project cycle is active.
- Imports departmental student records from XLSX/CSV files and adds or corrects records manually.
- Reviews student registrations that cannot be verified automatically.
- Assigns supervisors to verified students before topic submission.
- Reviews supervisor workload information and decides allocations; the system does not impose a fixed supervision cap or automatically allocate students.
- Reassigns supervisors when necessary. A reason is mandatory and the full allocation history is retained.
- Defines the common project milestones and major project deadlines for each academic session.
- Reviews and decides student deadline-extension requests.
- Creates examination panels, assigns lecturers to panels and allocates cleared students to panels.
- Grants or withholds final departmental defence clearance after receiving the supervisor's recommendation.
- Reviews and approves calculated examination results before publication.
- Makes the final administrative decision on result appeals after examination-panel review.

### 3.3 Lecturer / Project Supervisor / Examiner
A lecturer may perform different academic functions depending on their assignments.

As a supervisor, a lecturer:
- Reviews topic proposals submitted by their assigned students.
- Approves a proposal, requests revision or rejects it.
- Reviews chapter submissions in any order and provides written feedback and/or annotated-document feedback.
- Reviews milestone progress reports and records progress assessments.
- Recommends or does not recommend a completed project for defence.
- Configures assessment components and maximum marks for their supervisees in an academic session. The same configuration applies to all students assigned to that supervisor in that session.
- Does **not** award the examination marks for their own supervisees.
- Cannot add individual milestones to the session-wide milestone structure.

As an examiner, a lecturer:
- Serves on panels to which the Project Coordinator assigns them.
- Independently scores every configured assessment component for each student assigned to the panel.
- Can view and correct only their own submitted scores when a result is returned for correction.
- Cannot examine or score a student they supervise.

### 3.4 Student
- Self-registers using their academic details, including matriculation number.
- Completes automatic or manual verification before using student project functions.
- Views their assigned supervisor.
- Submits an independently developed project topic after supervisor allocation.
- Submits and resubmits chapters in any order.
- Views supervisor feedback and annotated documents.
- Submits progress reports at defined project milestones.
- Submits the complete final project to their supervisor.
- Requests deadline extensions with a reason and proposed revised deadline.
- Views published overall and component results, but not individual examiner scores.
- Submits a result complaint within the appeal window.

## 4. Functional requirements

### FR-01 — Account creation and access
1. The initial Administrator account is established through controlled system setup.
2. The Administrator creates Project Coordinator accounts.
3. The Administrator and/or Project Coordinator create lecturer accounts.
4. Students self-register.
5. The system supports the four existing roles: Administrator, Project Coordinator, Lecturer and Student.
6. The existing account foundation permits multiple global roles for one account where authorised.
7. Unverified student accounts must not access protected student project functions.

### FR-02 — Academic sessions
1. The system stores multiple academic sessions.
2. Only one session may have an active project cycle at a time.
3. The Coordinator controls opening, closing and archiving sessions.
4. Closing or archiving a session must not delete or overwrite its records.
5. New sessions must not alter historical student, project, submission, supervision, examination or result records.

### FR-03 — Departmental student register and verification
1. The Coordinator can import student records from XLSX and CSV files.
2. The Coordinator can create and edit individual student records manually.
3. Imported data must be validated, and duplicate matriculation numbers and invalid rows must be identified before records are committed.
4. A student registration is checked against the departmental register for the relevant academic session.
5. A valid matriculation-number match can be verified automatically.
6. Missing, inconsistent or unmatched records are referred to the Coordinator for manual review and approval or rejection.
7. The system retains the verification status and decision history.

### FR-04 — Supervisor allocation and reassignment
1. A verified student must be assigned a supervisor **before** submitting a project topic.
2. The Coordinator makes the allocation decision.
3. The system displays each lecturer's current supervision workload to support the Coordinator's decision.
4. The system does not automatically allocate students and does not enforce a fixed maximum number of supervisees.
5. The Coordinator may reassign a student at any time.
6. A reassignment reason is mandatory.
7. The system preserves the previous assignment, new assignment, assigning Coordinator, reason and timestamps.
8. The current supervisor receives access to the student's active supervision records; historical allocation records remain preserved.

### FR-05 — Project topic proposal and approval
1. Each student manages an individual project.
2. Only a student with a current supervisor assignment may submit a topic proposal.
3. A proposal captures, at minimum, the project title, abstract, problem statement, research objectives and keywords.
4. The assigned supervisor is the academic authority for topic review and approval. The Project Coordinator does not approve topics.
5. The supervisor may **Approve**, **Request Revision** or **Reject** a proposal.
6. A revision request returns the proposal to the student for editing and resubmission.
7. A rejection requires the student to submit a new topic proposal.
8. Proposal versions, decisions, supervisor comments and timestamps are retained.

### FR-06 — Topic similarity detection
1. On proposal submission, the system compares the proposal with proposals from the current and all previous academic sessions.
2. Comparison covers title, abstract, problem statement, research objectives and keywords.
3. Detection combines keyword matching and semantic similarity analysis.
4. The detection engine runs locally within the Django application infrastructure; no external AI API is required for this feature.
5. Similarity thresholds are system-defined and consistent across sessions; they are not configurable by users.
6. Similarity results are advisory and must not automatically reject a proposal.
7. Only the assigned supervisor can view the similarity report. Students and the Project Coordinator cannot view the report.
8. The supervisor report shows matched historical project title, academic session, similarity percentage, project status and relevant matched sections. It does not expose the complete historical project document.
9. The supervisor remains responsible for the final academic judgement.

### FR-07 — Chapter submissions and supervision feedback
1. Students may submit individual chapters in any order.
2. A student does not need approval of one chapter before submitting another.
3. Students may submit corrected versions of a chapter.
4. A submission has exactly one mandatory primary document and may include up to five supporting files.
5. Each individual file is limited to 20 MB.
6. Permitted file formats are fixed by the system for each submission category (see Section 8).
7. Supervisors can provide written feedback in ProjFlow and upload annotated documents prepared externally.
8. Original submissions, revised versions, feedback and timestamps are retained as history.

### FR-08 — Milestone-based progress monitoring
1. Progress reporting is milestone-based, not weekly or monthly.
2. The Coordinator defines the milestone structure for each academic session.
3. The same session-wide milestone structure applies to all students in that session.
4. Supervisors cannot add individual milestones or alter the session-wide milestone structure.
5. The Coordinator defines milestone titles, descriptions and deadlines.
6. Students submit progress reports when reporting against the relevant milestones.
7. Supervisors review reports, provide feedback and record progress assessments.
8. Milestone completion and review history are retained.
9. Milestone reporting does not impose sequential chapter-submission or chapter-approval rules.

### FR-09 — Project deadlines and extensions
1. The Coordinator sets and manages major project activity deadlines for each academic session.
2. The system displays relevant deadlines to students and identifies overdue activities.
3. Students may request an extension before or after the original deadline expires.
4. An extension request must include a reason and proposed revised deadline.
5. The Coordinator approves or rejects each request.
6. Submitting a request does not itself extend a deadline.
7. An approved extension applies to the relevant student and activity.
8. Original deadline, requested deadline, approved deadline, reason, decision and timestamps are retained.

### FR-10 — Final project submission and defence clearance
1. The student submits the complete final project to their assigned supervisor.
2. The supervisor reviews the final project and records a recommendation for or against defence.
3. The Project Coordinator reviews the recommendation and grants or withholds final departmental defence clearance.
4. Only students granted final clearance may be allocated to a defence panel and scheduled for defence.
5. Supervisor recommendation and Coordinator clearance records are retained.

### FR-11 — Examination panel management
1. The Coordinator creates examination panels.
2. The Coordinator assigns lecturers to panels and allocates cleared students to panels.
3. A student's supervisor must not be a member of the panel examining that student.
4. The system validates panel assignments against current supervisor assignments and prevents this conflict of interest.
5. Panel membership, student allocation and defence scheduling history are retained.

### FR-12 — Assessment configuration and scoring
1. Each supervisor configures an assessment structure for their supervisees within an academic session.
2. The structure contains one or more assessment components, each with a maximum mark.
3. The sum of component maximum marks must equal exactly 100.
4. The same assessment structure applies to all students assigned to that supervisor in that session.
5. Assessment-structure changes must be authorised and recorded in an audit history; the active structure must not be silently changed after marks have been recorded.
6. Examination panel members, not supervisors, award marks.
7. Every panel member independently scores every configured component for each student assigned to that panel.
8. Each examiner can submit and correct only their own scores.
9. The system calculates the average examiner score for each component.
10. The overall project score is the sum of the component averages and is out of 100.
11. Individual examiner scores remain confidential from students.

### FR-13 — Result approval, publication and correction
1. Calculated results are submitted to the Project Coordinator for review.
2. Results remain unpublished until the Coordinator explicitly approves them.
3. The Coordinator cannot directly edit examiner scores.
4. If correction is required, the Coordinator returns the result to the examination panel.
5. Each examiner may correct only their own scores.
6. The system recalculates component averages and the overall result after corrections.
7. The corrected result returns to the Coordinator for approval.
8. Students can view the overall score and component scores after publication.
9. Students cannot view individual examiner scores.
10. Original scores, corrected scores, correction reasons, approvals and publication timestamps are retained.

### FR-14 — Result complaints and appeals
1. A student may submit a formal result complaint within 14 calendar days after publication.
2. The complaint is referred to the examination panel for review.
3. The panel records findings and a recommendation.
4. The Project Coordinator makes the final administrative decision.
5. If a score change is authorised, the normal examiner correction and result approval workflow applies.
6. Complaint, review and resolution records are retained.

### FR-15 — Notifications
1. The system supports both in-app and email notifications.
2. Notifications cover relevant events such as supervisor allocation, topic decisions, chapter feedback, deadlines, extension decisions, defence scheduling, result publication and appeals.
3. Users can enable or disable individual notification categories in their preferences.
4. Preferences are stored per user account.

### FR-16 — Document storage and access
1. Academic documents are stored in private Supabase Storage buckets.
2. PostgreSQL stores document metadata and storage references, not document binaries.
3. Django performs authentication and project-level authorisation before issuing or permitting file access.
4. Student access is limited to their own project documents.
5. Supervisor access is limited to current supervisees' project documents.
6. The Project Coordinator can access departmental project documents for authorised administration.
7. Examination panel members can access documents for students allocated to their panels.
8. The system must not expose public storage URLs for private academic documents.

## 5. Business rules and key constraints

| ID | Rule |
|---|---|
| BR-01 | One department is in scope. |
| BR-02 | One active project cycle at a time. |
| BR-03 | Projects are individual, not group-based. |
| BR-04 | A supervisor is assigned before topic submission. |
| BR-05 | The Coordinator allocates supervisors; no fixed workload cap is enforced. |
| BR-06 | Reassignment requires a reason and preserves history. |
| BR-07 | Only the assigned supervisor approves a topic. |
| BR-08 | Chapter submissions are not sequentially gated. |
| BR-09 | Session-wide milestones are defined only by the Coordinator. |
| BR-10 | Assessment component maxima sum to exactly 100. |
| BR-11 | Panel members independently score all components; the system averages scores per component. |
| BR-12 | A supervisor cannot examine their own supervisee. |
| BR-13 | Results require Coordinator approval before publication. |
| BR-14 | Appeals close 14 days after publication. |
| BR-15 | One primary file plus at most five supporting files per submission. |
| BR-16 | Each uploaded file is at most 20 MB. |

## 6. Non-functional requirements

- **Security:** Authentication, role-based and object-level authorisation, secure password handling, HTTPS, private document storage and auditability for sensitive actions.
- **Privacy:** Student records, proposals, submissions, marks and documents must not be exposed to users without a legitimate role and project relationship.
- **Integrity:** Database constraints and transactional operations must protect session uniqueness, active supervisor assignments, assessment totals and result state transitions.
- **Reliability:** Historical academic records and submission versions must not be overwritten by routine updates.
- **Usability:** Interfaces must be responsive and provide clear validation and workflow status messages.
- **Maintainability:** The backend remains a modular monolith with domain-separated Django applications and a documented REST API.
- **Performance:** Topic similarity calculations should reuse stored embeddings and avoid re-embedding unchanged historical proposals on every submission.
- **Auditability:** Supervisor reassignment, milestone/deadline changes, assessment configuration changes, examiner score corrections, result approval and appeal decisions must be traceable.

## 7. Core workflows

### 7.1 Student onboarding and supervisor allocation

1. Coordinator opens the academic session and imports or enters the departmental student register.
2. Student self-registers with their matriculation number and academic details.
3. The system verifies a matching register entry automatically; exceptions go to the Coordinator for manual review.
4. After verification, the Coordinator assigns a supervisor based on workload information and their administrative judgement.
5. The student can then submit a topic proposal.

### 7.2 Topic review

1. Student submits proposal to the assigned supervisor.
2. Local similarity analysis compares the proposal against historical proposals.
3. Similarity results are visible only to the assigned supervisor.
4. Supervisor approves, requests revision or rejects the proposal.
5. Student proceeds to project development after approval.

### 7.3 Development and progress

1. Student submits chapters in any order.
2. Supervisor reviews and gives written and/or annotated feedback.
3. Student reports progress against Coordinator-defined milestones.
4. Supervisor reviews milestone reports and records progress assessments.
5. Student may request deadline extensions; the Coordinator decides.

### 7.4 Final submission, defence and results

1. Student submits the complete project to the supervisor.
2. Supervisor recommends or does not recommend defence.
3. Coordinator grants or withholds final clearance.
4. Coordinator creates panels and allocates cleared students, excluding each student's own supervisor from their panel.
5. Panel members independently score every assessment component.
6. ProjFlow calculates component averages and the overall score.
7. Coordinator approves results before publication.
8. Students may appeal within 14 days; the panel reviews and the Coordinator decides.

## 8. File upload policy

### 8.1 Fixed file-format mapping

| Submission category | Permitted formats |
|---|---|
| Project topic proposal | PDF, DOC, DOCX |
| Chapter submissions | PDF, DOC, DOCX |
| Revised chapters | PDF, DOC, DOCX |
| Supervisor annotated feedback | PDF, DOC, DOCX |
| Final project report | PDF, DOC, DOCX |
| Defence presentation | PPTX, PDF |
| Supplementary materials | PDF, DOC, DOCX, XLSX, JPG, JPEG, PNG |

The mapping is system-defined and cannot be changed through the user interface by the Coordinator or supervisors.

### 8.2 Per-submission limits

- Exactly one primary document is mandatory.
- Up to five optional supporting files are permitted.
- Every individual file, including the primary document, must be no larger than 20 MB.
- The backend validates the file extension, detected file type and size; frontend-only validation is insufficient.

## 9. Existing implementation baseline

The uploaded archive contains release 0.1.0: React/Vite frontend, Django 5.2/DRF backend, Supabase PostgreSQL configuration, custom UUID-based email user model, four seeded roles, admin foundation, health/readiness endpoints and deployment configuration. The academic workflows in this specification are not yet implemented.

The implementation must extend this foundation rather than replace it without a demonstrated technical need.

## 10. Items to settle during implementation/testing, not blockers to the approved workflow

The following technical values were not fixed during requirements planning and should be selected through implementation evidence rather than another round of broad requirements questions:

- Exact numerical thresholds for topic similarity and the final lightweight embedding model; establish these through a representative test corpus and false-positive/false-negative evaluation.
- Exact mandatory fields and validation rules for the department's student register beyond matriculation number and student identity; align these with the actual departmental roster format.
- The transactional email provider and production sender configuration.
- Detailed grading labels or class boundaries, if the department requires them; the approved numeric score is out of 100.
- Detailed deployment resource sizing for local NLP inference; benchmark the selected model on the target Render service before production activation.
