# ProjFlow

**From Proposal to Final Defence.**

ProjFlow is a web-based final-year project management system designed to coordinate the administration, supervision, submission, examination, assessment, and publication of final-year undergraduate projects within a single academic department.

## Project status

**Stage:** Initial repository foundation  
**Version:** 0.1.0-pre-development

The repository is being established before application implementation. Requirements and system design are being finalised so that implementation follows an agreed baseline.

## Approved technology direction

- **Frontend:** React, Vite, React Router
- **Backend:** Python, Django, Django REST Framework
- **Database:** PostgreSQL
- **API style:** REST
- **Architecture:** Modular monolith

Exact dependency versions and deployment configuration will be established during implementation.

## Initial scope

The system is intended to support:

- Departmental student registration and registration-number verification
- Lecturer records and flexible departmental responsibilities
- Supervisor allocation and topic approval
- Project chapter and complete-document submissions
- Supervision reviews, feedback, and version history
- Configurable final submission deadline and audited exceptional reopening
- Examination groups, panels, panel membership, and scheduling
- Individual examiner assessments and panel-agreed criterion scores
- Configurable assessment and grading schemes
- Controlled result review, publication, and correction

The system is scoped to one department for the initial implementation. Features outside the approved project-management scope will not be added without an explicit decision.

## Repository structure

```text
projflow/
├── backend/                 # Django backend (implementation to follow)
├── frontend/                # React frontend (implementation to follow)
├── docs/
│   ├── architecture/
│   ├── database/
│   ├── requirements/
│   └── branding/
├── .gitignore
└── README.md
```

## Development principles

1. Enforce authorisation on the backend; frontend route guards are not security boundaries.
2. Keep student records, project documents, assessment records, credentials, and backups private.
3. Never commit `.env` files, secrets, real student data, or uploaded academic documents.
4. Use synthetic data for demonstrations and tests.
5. Preserve audit histories for sensitive academic and administrative operations.
6. Implement and test modules incrementally.

## Branding

The approved initial identity is documented in [`docs/branding/BRAND-GUIDELINES.md`](docs/branding/BRAND-GUIDELINES.md).

The primary logo, reversed logo, monochrome logo, symbol, app icon, favicon exports, and CSS design tokens are included in `docs/branding/`.

## Security and privacy

This is a public source-code repository. Public visibility does not make application data public. Production data and uploaded documents must be stored in appropriately protected services and must never be committed to this repository.

Do not add API keys, database passwords, Django secret keys, personal data, or real academic records to Git history.

## Licence

No open-source licence has been selected yet. Until a licence is added, do not assume that the code may be reused, redistributed, or incorporated into other projects.
