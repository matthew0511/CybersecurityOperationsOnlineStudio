# Program owner attribution

Program Owner - Matthew Harris is fixed in application source, displayed on the sign-in screen, workspace header and footer, and included in the shared executive/board PDF and Excel report footers.

The attribution is independent of signed-in usernames and organization records. There is no application preference, form field, or API operation for changing or removing it. The production container serves the bundled source from its read-only filesystem.

This protects the attribution from removal through normal application use. Repository and deployment administrators can still modify or replace source code; absolute removal prevention against those administrators is not technically possible.

## Validation — 31 October 2026

- Pinned application source: `cc50bcbaab332d4883664fb932a0d556630688f3`.
- CodeBuild `cyber-ops-online-studio-web:24bc7590-0d70-4839-bcdc-f7ebe2efa14c`: 53 backend tests, four interface calculation tests and the read-only non-root container smoke test passed.
- Image `owner-20261031-v1`, digest `sha256:e79aaa02e493db6f2da76d781f637284970cc49b0b179a9b2279236533aa0b66`: ECR scan completed with no findings at validation time.
- Export checks: attribution extracted from both executive and board PDFs and found in every sheet footer of both Excel exports. The board PDF footer was also visually inspected.
- Live custom domain and AWS gateway both serve all three fixed HTML attribution placements and return ready with the database connected. The sign-in attribution was verified in the browser. No production owner credentials were used.
