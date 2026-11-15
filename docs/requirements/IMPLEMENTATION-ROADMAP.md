# ProjFlow implementation roadmap

The roadmap sequences implementation around dependencies. It is not a request for additional requirements decisions; the approved SRS is the baseline.

| Phase | Scope | Main output |
|---|---|---|
| 0 | Requirements and architecture baseline | Approved SRS, architecture decisions and conceptual database model |
| 1 | Academic foundation | Academic sessions, student roster import/manual entry, student enrolment/verification, lecturer profiles and supervisor assignment history |
| 2 | Topic management | Project records, proposal versions, supervisor review decisions and local topic similarity engine |
| 3 | Supervision and submissions | Chapter/final submissions, private file storage, annotated feedback, deadlines/extensions and milestone reports |
| 4 | Defence management | Final clearance, panel setup, panel membership, student allocation, scheduling and supervisor conflict validation |
| 5 | Assessment and results | Supervisor-configured 100-mark templates, independent examiner scoring, averages, approval, publication, correction and appeals |
| 6 | Notifications and dashboards | In-app/email delivery, preferences, role dashboards, monitoring and operational summaries |
| 7 | Verification and deployment | Security review, end-to-end tests, load/resource checks, documentation and deployment hardening |

## Phase 1 implementation order

1. Resolve the SPA authentication design before exposing registration and protected frontend workflows. The current 0.1.0 cross-origin settings are not sufficient for authenticated React requests.
2. Add academic session models and the one-active-cycle database constraint.
3. Add departmental student roster records and validated XLSX/CSV import services.
4. Add student enrolment and automatic/manual verification states.
5. Add lecturer profiles and supervisor assignment history, including mandatory reassignment reasons.
6. Add API permissions and tests for Coordinator-only operations and student/lecturer data boundaries.

Each phase should include migrations, model/service tests, API permission tests, documentation updates and a frontend production build before being treated as complete.
