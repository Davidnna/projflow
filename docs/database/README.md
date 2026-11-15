# ProjFlow database design

This is the conceptual data model for the approved requirements. Physical field definitions and Django migrations will be added with each implementation slice. UUID primary keys and explicit foreign-key relationships should be used consistently with the existing account foundation.

## 1. Existing account entities

- **User** — UUID identity, email login, password hash, names and account status.
- **Role** — Administrator, Project Coordinator, Lecturer or Student.
- **UserRole** — many-to-many role assignment, including who assigned the role and when.

## 2. Academic administration entities

| Entity | Purpose | Important relationships / constraints |
|---|---|---|
| `AcademicSession` | Represents one academic session/project cycle | Multiple sessions retained; conditional uniqueness allows at most one active session |
| `StudentRosterRecord` | Authoritative eligible-student record imported or entered by Coordinator | Belongs to a session; matriculation number unique within session |
| `StudentEnrollment` | Links a registered student account to a session and roster record | Unique student/session and unique matriculation/session; stores verification state |
| `LecturerProfile` | Lecturer-specific data attached to a user | One-to-one with user |
| `SupervisorAssignment` | Current and historical supervisor allocation | Belongs to an enrolment; only one current assignment per enrolment; reassignment reason and history retained |
| `ProjectMilestone` | Session-wide progress milestone | Belongs to session; created/managed by Coordinator; common to all students in session |
| `MilestoneProgressReport` | Student report and supervisor review for a milestone | Links enrolment, milestone and reviewer; retains report/review history |
| `ProjectDeadline` | Session-level deadline for an activity | Coordinator-managed; may be associated with a milestone or submission category |
| `DeadlineExtensionRequest` | Student request and Coordinator decision | Preserves original deadline, requested date, reason and decision |

## 3. Project and supervision entities

| Entity | Purpose | Important relationships / constraints |
|---|---|---|
| `StudentProject` | Individual project record for an enrolment | One-to-one with student enrolment |
| `TopicProposal` | Proposal version containing title, abstract, problem, objectives and keywords | Belongs to project; multiple versions/history permitted |
| `TopicReview` | Supervisor decision and comments | Approve, request revision or reject; reviewer must be current assigned supervisor |
| `ProposalEmbedding` | Stored lexical/semantic representation of a proposal version | One representation per processed version/model; enables reuse |
| `TopicSimilarityMatch` | Similar historical proposal match and score | Links submitted version to historical version; report access restricted to assigned supervisor |

## 4. Submission and document entities

| Entity | Purpose | Important relationships / constraints |
|---|---|---|
| `ProjectSubmission` | Chapter, revised chapter or final-project submission | Belongs to project; category-specific state and timestamps |
| `SubmissionFile` | Primary or supporting document metadata | Exactly one primary file per submission; at most five supporting files; each no larger than 20 MB; stores private Supabase object key |
| `SupervisorFeedback` | Written comments and review decision | Links supervisor to submission; feedback versions retained |
| `AnnotatedFeedbackFile` | Supervisor-uploaded annotated document | Private storage reference and metadata |

Document binaries remain in Supabase Storage. PostgreSQL stores metadata and object keys only.

## 5. Examination and assessment entities

| Entity | Purpose | Important relationships / constraints |
|---|---|---|
| `DefenceClearance` | Supervisor recommendation and Coordinator clearance | Student cannot be panel-allocated until cleared |
| `ExaminationPanel` | Panel created by Coordinator | Belongs to academic session |
| `PanelMembership` | Lecturer membership of panel | Unique panel/lecturer pair |
| `PanelStudentAllocation` | Student allocated to panel and schedule | Must be cleared; constraint/service validation prevents the student's supervisor from panel membership |
| `AssessmentTemplate` | Supervisor's assessment structure for a session | Unique supervisor/session; total component maxima exactly 100; shared by all that supervisor's supervisees in session |
| `AssessmentComponent` | Named component and maximum mark | Belongs to template; component maximum is positive |
| `ExaminerScore` | One examiner's independent score for one student/component | Unique examiner/student/component/assessment event; score cannot exceed component maximum; examiner must be assigned panel member and not student's supervisor |
| `ComponentResult` | Average examiner score for a component | Calculated from submitted valid examiner scores; not manually edited |
| `ProjectResult` | Overall score and publication state | Sum of component averages; Coordinator approval required before publication |
| `ResultCorrection` | Returned result and examiner corrections | Examiner may change only their own score; old values and reasons retained |
| `ResultAppeal` | Student complaint and panel/Coordinator decision | Submission allowed within 14 days after publication |

## 6. Notification and audit entities

- **Notification** — recipient, category, message, in-app read state, related object and creation time.
- **NotificationPreference** — per-user, per-category in-app/email preference state.
- **AuditEvent** — actor, action, target object, timestamp and relevant before/after metadata for sensitive changes.

## 7. Core integrity constraints

1. At most one `AcademicSession` has an active project cycle.
2. A student has at most one enrolment per academic session and one individual project per enrolment.
3. A student enrolment has at most one current supervisor assignment; historical assignments are retained.
4. A topic cannot be submitted until a current supervisor assignment exists.
5. A topic review can be made only by the assigned supervisor.
6. A milestone is session-wide; supervisors cannot create student-specific milestone definitions.
7. Each submission has one primary file and no more than five supporting files; each file is at most 20 MB.
8. Each supervisor has one assessment template per academic session; component maxima sum to 100.
9. Each examiner can score only students assigned to their panel and cannot score their own supervisees.
10. Result publication requires Coordinator approval.
11. Appeal submission is limited to 14 days after publication.
12. Document access must be checked against the user's role and project relationship on every request.

## 8. Migration approach

- Preserve the existing `accounts` schema and its UUID keys.
- Add domain models in small, testable Django applications.
- Generate and review migrations for each implementation slice.
- Use database constraints for invariants that can be expressed at the database layer and transactional service logic for multi-row workflow rules.
- Never rewrite historical project or assessment records as a shortcut for updating current state.
