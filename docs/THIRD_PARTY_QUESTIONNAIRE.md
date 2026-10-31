# Default third-party risk questionnaire

The owner-supplied CSV contains 60 questions and a Multi-Line type for every row. All questions are included in source order, including contact information, HIPAA, data protection, testing, vendors, physical security, incidents, training, compliance, insurance, and appointment follow-up. Only surrounding whitespace is trimmed.

In the online workspace choose Assessments → New third-party questionnaire, enter a title and scope, and save. Alternatively use Create Assessment and select Third-party risk assessment — Default (60 questions) in Template Id. Select the created questionnaire below the records table to answer each question, then use Save response for each edited answer. A saved-response count shows progress. Responses are limited to 5,000 characters each.

The built-in ID is `builtin:third-party-risk-v1`. Each new assessment receives an independent snapshot, stable codes TPR-001 through TPR-060, and a creation audit event. Existing assessments and custom templates are unchanged. The default requires no CSV import or organization-specific setup.

Narrative responses are stored in the existing rationale field and use the existing Unknown status to indicate unscored responses; blank responses use Unanswered. They are not automatic Yes/No judgments, compliance certifications, or numeric risk ratings. Reviewer risk decisions remain separate. Existing reports may describe these as Unknown; use the questionnaire response count for narrative completion.
