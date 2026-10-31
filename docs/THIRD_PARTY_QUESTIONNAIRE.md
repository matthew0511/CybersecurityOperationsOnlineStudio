# Default third-party risk questionnaire

The owner-supplied CSV contains 60 questions and a Multi-Line type for every row. All questions are included in source order, including contact information, HIPAA, data protection, testing, vendors, physical security, incidents, training, compliance, insurance, and appointment follow-up. Only surrounding whitespace is trimmed.

In the online workspace choose Assessments → New third-party questionnaire, enter a title and scope, and save. Alternatively use Create Assessment and select Third-party risk assessment — Default (60 questions) in Template Id. Select the created questionnaire below the records table to answer each question, then use Save response for each edited answer. A saved-response count shows progress. Responses are limited to 5,000 characters each.

The built-in ID is `builtin:third-party-risk-v1`. Each new assessment receives an independent snapshot, stable codes TPR-001 through TPR-060, and a creation audit event. Existing assessments and custom templates are unchanged. The default requires no CSV import or organization-specific setup.

Narrative responses are stored in the existing rationale field and use the existing Unknown status to indicate unscored responses; blank responses use Unanswered. They are not automatic Yes/No judgments, compliance certifications, or numeric risk ratings. Reviewer risk decisions remain separate. Existing reports may describe these as Unknown; use the questionnaire response count for narrative completion.

## Build validation — October 31, 2026

- AWS CodeBuild `cyber-ops-online-studio-web:d1fab352-7ae8-4b7a-b5df-d4730cfa1be7`: SUCCEEDED; 53 tests passed, including PostgreSQL API response persistence.
- Source commit: `9b18381533031b238e8a8980dd14fd91f663dd00`; merged through PR #1.
- Image: `online-20261031-tpr-v1`; digest `sha256:e5473ad80559cda28a05bea0e3e9a8a1ffecd93254e4bddd221ce0fccf9dab63`.
- ECR scan: COMPLETE, no findings at validation time. Non-root/read-only database and temporary-volume smoke test passed.
- No schema migration is needed. Live browser authentication and questionnaire entry were tested against the isolated PostgreSQL integration database, not through the real owner's production session.

This build used CodeBuild source overrides `GITHUB`, repository `https://github.com/matthew0511/CybersecurityOperationsOnlineStudio.git`, and the pinned source commit above. The project's configured S3 source archive was not replaced; future builds must supply the intended GitHub source override or refresh that archive before building. Use a new immutable image tag for each release.
